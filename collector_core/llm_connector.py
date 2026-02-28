"""Provider-agnostic async connector for LLM text generation and summarization.

Example:
    ```python
    import asyncio
    from collector_core.llm_connector import LLMConnector

    async def main() -> None:
        connector = LLMConnector(model="openai/gpt-4o-mini", temperature=0.1)
        summary = await connector.summarize(
            "Langer Quelltext fuer die Zusammenfassung ...",
            sentences_count=4,
            language="Deutsch",
        )
        print(summary)

    asyncio.run(main())
    ```

Tolerant API behavior:
    Optional numeric connector settings are normalized defensively.
    Invalid values for `timeout_seconds` or `max_retries` fall back to defaults.
    Invalid values for `temperature` are treated like `None`.
    All fallbacks are logged as warnings instead of raising configuration exceptions.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from collections import deque
from typing import Any, Final

import litellm

LOGGER = logging.getLogger(__name__)

RATE_LIMIT_MAX_CALLS: int | None = 20
RATE_LIMIT_WINDOW_SECONDS: int = 30
REQUEST_TIMEOUT_SECONDS: float = 60.0
MAX_RETRIES: int = 3
RETRY_BASE_DELAY_SECONDS: float = 1.0
RETRY_MAX_DELAY_SECONDS: float = 8.0
RETRY_JITTER_MIN_SECONDS: float = 0.25
RETRY_JITTER_MAX_SECONDS: float = 2.0


DEFAULT_SYSTEM_PROMPT: Final[str] = (
    "Du bist ein präziser Assistent für politische und juristische Texte. "
    "Antworte klar, faktenorientiert. "
    "Füge keine Formatierungen oder Hervorhebungen hinzu. "
    "Antworte nur mit dem reinen Text, ohne Einleitungen oder Erklärungen. "
    "Die Antwort darf nur die direkt angeforderten Informationen enthalten. "
    "Spekulationen oder Annahmen sind zu vermeiden."
)


class LLMConnectorError(RuntimeError):
    """Base exception for connector-level errors."""


class LLMResponseParseError(LLMConnectorError):
    """Raised when a provider response cannot be parsed as text."""


class LLMProviderError(LLMConnectorError):
    """Raised when the LLM provider returns a known request/response failure."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when provider authentication or authorization fails."""


class LLMQuotaExceededError(LLMProviderError):
    """Raised when provider quota/budget is exhausted."""


class LLMRateLimitError(LLMProviderError):
    """Raised when provider-side rate limits are exceeded."""


class LLMTemporaryProviderError(LLMProviderError):
    """Raised for transient provider failures (timeout/network/5xx)."""


class RateLimiter:
    """Limit async calls to `max_calls` within `per_seconds`."""

    def __init__(self, max_calls: int, per_seconds: float) -> None:
        """Create a local async sliding-window rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in one window.
            per_seconds: Window size in seconds.

        Raises:
            ValueError: If `max_calls` is not a positive integer or `per_seconds`
                is not a positive numeric value.
        """
        if not isinstance(max_calls, int) or isinstance(max_calls, bool):
            raise ValueError("max_calls must be an integer")
        if max_calls <= 0:
            raise ValueError("max_calls must be greater than 0")

        try:
            normalized_per_seconds: float = float(per_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("per_seconds must be a number") from exc
        if normalized_per_seconds <= 0:
            raise ValueError("per_seconds must be greater than 0")

        self.max_calls: int = max_calls
        self.per_seconds: float = normalized_per_seconds
        self._timestamps: deque[float] = deque()
        self._lock: asyncio.Lock = asyncio.Lock()
        LOGGER.debug(
            "Initialized rate limiter (max_calls=%s, per_seconds=%s)",
            self.max_calls,
            self.per_seconds,
        )

    async def acquire_slot(self) -> None:
        """Wait until one call slot is available and reserve it.

        Returns:
            None
        """
        while True:
            async with self._lock:
                now = time.monotonic()
                cutoff = now - self.per_seconds

                removed_count = 0
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()
                    removed_count += 1
                if removed_count:
                    LOGGER.debug("Rate limiter removed %s expired slots", removed_count)

                if len(self._timestamps) < self.max_calls:
                    self._timestamps.append(now)
                    LOGGER.debug(
                        "Rate limiter granted slot (%s/%s in current window)",
                        len(self._timestamps),
                        self.max_calls,
                    )
                    return

                wait_seconds = self.per_seconds - (now - self._timestamps[0])
                LOGGER.debug(
                    "Rate limiter reached limit (%s/%s); waiting %.3fs",
                    len(self._timestamps),
                    self.max_calls,
                    max(wait_seconds, 0.0),
                )

            await asyncio.sleep(max(wait_seconds, 0.0))


class LLMConnector:
    """Thin provider-agnostic connector for async text generation via LiteLLM.

    Notes:
        Configuration is intentionally tolerant. Invalid `timeout_seconds` and
        `max_retries` values are replaced by defaults. Invalid `temperature`
        values are treated as `None`. All fallbacks are logged as warnings.
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        temperature: float | None = None,
        rate_limit_max_calls: int | None = RATE_LIMIT_MAX_CALLS,
        rate_limit_window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """Initialize a provider-specific text generation connector.

        Args:
            model: Fully-qualified model identifier (for example `openai/gpt-4o-mini`).
            api_key: API key for the provider. If `None`, relies on litellm's built-in
                provider key resolution. Empty/whitespace/non-string values are treated
                like `None`.
            temperature: Temperature of generated text (maps to provider temperature).
                Lower values are usually more deterministic.
            rate_limit_max_calls: Optional max number of async calls in the configured
                time window.
            rate_limit_window_seconds: Length of the async rate-limit window in seconds.
            timeout_seconds: Timeout per provider call in seconds. Invalid values
                fall back to `REQUEST_TIMEOUT_SECONDS`.
            max_retries: Number of retry attempts for retryable provider errors.
                Invalid values fall back to `MAX_RETRIES`.

        Notes:
            If local rate-limiter initialization fails due to invalid rate-limit
            configuration, rate-limiting is disabled (`self._rate_limiter = None`).
        """
        self.model = self._require_non_empty_text(model, field_name="model")
        self.api_key = self._validate_api_key(api_key)
        self.temperature = float(temperature) if temperature is not None else None
        self.timeout_seconds: float = self._validate_timeout_seconds(timeout_seconds)
        self.max_retries: int = self._validate_max_retries(max_retries)
        self._validate_retry_delay_constants()
        self._rate_limiter: RateLimiter | None = self._initialize_rate_limiter(
            rate_limit_max_calls=rate_limit_max_calls,
            rate_limit_window_seconds=rate_limit_window_seconds,
        )

        LOGGER.info(
            "Initialized LLMConnector (model=%s, api_key_set=%s, rate_limit_enabled=%s, timeout=%.1fs, max_retries=%s)",
            self.model,
            self.api_key is not None,
            self._rate_limiter is not None,
            self.timeout_seconds,
            self.max_retries,
        )

    def _initialize_rate_limiter(
        self, rate_limit_max_calls: int | None, rate_limit_window_seconds: float
    ) -> RateLimiter | None:
        """Initialize local rate limiting and gracefully fall back to no limiter.

        Args:
            rate_limit_max_calls: Maximum calls within one local time window.
                `None` disables local rate limiting.
            rate_limit_window_seconds: Length of the local rate-limit window.

        Returns:
            A configured `RateLimiter` instance, or `None` if local limiting is disabled
            or cannot be initialized from the provided values.
        """
        if rate_limit_max_calls is None:
            LOGGER.info("Local rate limiting is disabled (max_calls=None)")
            return None

        try:
            return RateLimiter(rate_limit_max_calls, rate_limit_window_seconds)
        except ValueError as exc:
            LOGGER.warning(
                "Failed to initialize local rate limiter. Ignoring rate limiting "
                "(max_calls=%s, window_seconds=%s): %s",
                rate_limit_max_calls,
                rate_limit_window_seconds,
                exc,
            )
            return None

    async def generate_text(
        self, prompt: str, system_prompt: str | None = DEFAULT_SYSTEM_PROMPT
    ) -> str:
        """Generate text using the configured model.

        Args:
            prompt: User input prompt for the model.
            system_prompt: Optional system-level instruction for model behavior.
                If empty/whitespace or `None`, no system message is sent.

        Returns:
            The generated plain-text model output.

        Raises:
            ValueError: If prompt/system prompt validation fails.
            LLMProviderError: If provider call fails and cannot be recovered by retries.
            LLMResponseParseError: If provider response structure cannot be parsed.
        """
        normalized_prompt = self._require_non_empty_text(prompt, field_name="prompt")
        normalized_system_prompt: str | None = None
        if system_prompt is not None:
            if not isinstance(system_prompt, str):
                raise ValueError("system_prompt must be a string or None")
            stripped_system_prompt = system_prompt.strip()
            if stripped_system_prompt:
                normalized_system_prompt = stripped_system_prompt

        messages: list[dict[str, str]] = [{"role": "user", "content": normalized_prompt}]
        if normalized_system_prompt is not None:
            messages.insert(0, {"role": "system", "content": normalized_system_prompt})

        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "api_key": self.api_key,
            "messages": messages,
            "temperature": self.temperature,
            "timeout": self.timeout_seconds,
        }
        LOGGER.debug(
            "Starting text generation (model=%s, prompt_chars=%s, retries=%s)",
            self.model,
            len(normalized_prompt),
            self.max_retries,
        )

        response: litellm.ModelResponse | litellm.CustomStreamWrapper | None = None
        for attempt in range(self.max_retries + 1):
            if self._rate_limiter is not None:
                LOGGER.debug("Waiting for local rate limiter slot (attempt=%s)", attempt + 1)
                await self._rate_limiter.acquire_slot()

            try:
                LOGGER.debug(
                    "Calling provider (attempt=%s/%s, timeout=%.1fs)",
                    attempt + 1,
                    self.max_retries + 1,
                    self.timeout_seconds,
                )
                response = await asyncio.wait_for(
                    litellm.acompletion(**request_kwargs),
                    self.timeout_seconds + 0.5,
                )
                LOGGER.debug(
                    "Provider call successful (attempt=%s/%s)",
                    attempt + 1,
                    self.max_retries + 1,
                )
                break
            except (asyncio.TimeoutError, litellm.exceptions.Timeout) as exc:
                mapped_error: LLMProviderError = LLMTemporaryProviderError(
                    "provider request timed out"
                )
                original_error: Exception = exc
                LOGGER.warning(
                    "Provider timeout (attempt=%s/%s, timeout=%.1fs)",
                    attempt + 1,
                    self.max_retries + 1,
                    self.timeout_seconds,
                )
            except Exception as exc:
                mapped_error = self._map_provider_exception(exc)
                original_error = exc
                LOGGER.warning(
                    "Provider call failed (attempt=%s/%s, error_type=%s, mapped_error_type=%s) %s",
                    attempt + 1,
                    self.max_retries + 1,
                    type(exc).__name__,
                    type(mapped_error).__name__,
                    str(exc),
                )

            should_retry: bool = attempt < self.max_retries and (
                isinstance(mapped_error, (LLMRateLimitError, LLMTemporaryProviderError))
            )
            if not should_retry:
                LOGGER.error(
                    "Provider request failed without retry (attempt=%s/%s, error_type=%s)",
                    attempt + 1,
                    self.max_retries + 1,
                    type(mapped_error).__name__,
                )
                raise mapped_error from original_error

            backoff_seconds = self._compute_retry_delay(attempt)
            LOGGER.info(
                "Retrying provider call in %.2fs (next_attempt=%s/%s, error_type=%s)",
                backoff_seconds,
                attempt + 2,
                self.max_retries + 1,
                type(mapped_error).__name__,
            )

            await asyncio.sleep(backoff_seconds)

        if response is None:
            raise LLMConnectorError("unreachable retry loop state")
        if isinstance(response, (litellm.CustomStreamWrapper)):
            raise LLMConnectorError(
                f"Response type `CustomStreamWrapper` is not supported. Got: {type(response).__name__}"
            )
        return self._extract_text(response)

    async def summarize(
        self,
        text: str,
        language: str = "Deutsch",
        sentences_count: int | None = None,
        word_count: int | None = None,
        character_count: int | None = None,
    ) -> str:
        """Create a concise summary for an input text.

        Args:
            text: Source text to summarize.
            language: Target language for the summary output.
            sentences_count: Optional upper bound for sentence count. Invalid values are
                ignored.
            word_count: Optional upper bound for word count. Invalid values are ignored.
            character_count: Optional upper bound for character count. Invalid values are
                ignored.

        Returns:
            A concise generated summary.

        Raises:
            ValueError: If `text` is empty/invalid.
            LLMProviderError: If provider call fails and cannot be recovered by retries.
            LLMResponseParseError: If provider response structure cannot be parsed.

        Notes:
            If `language` is empty/invalid, the default language (`Deutsch`) is used.
            Count parameters are handled tolerant:
            - positive `float` values are truncated via `int(...)`
            - invalid values are ignored
        """
        source_text = self._require_non_empty_text(text, field_name="text")

        try:
            language_normalized = self._require_non_empty_text(language, field_name="language")
        except ValueError:
            LOGGER.warning(
                "Empty input language for summarization; using default language (Deutsch)"
            )
            language_normalized = "Deutsch"

        sentences_count = self._normalize_positive_count("sentences_count", sentences_count)
        word_count = self._normalize_positive_count("word_count", word_count)
        character_count = self._normalize_positive_count("character_count", character_count)
        LOGGER.debug(
            "Summarization request (language=%s, sentences=%s, words=%s, characters=%s, "
            "source_chars=%s)",
            language_normalized,
            sentences_count,
            word_count,
            character_count,
            len(source_text),
        )
        max_part = (
            (f"{sentences_count} Sätzen, " if sentences_count is not None else "")
            + (f"{word_count} Wörtern, " if word_count is not None else "")
            + (f"{character_count} Zeichen" if character_count is not None else "")
        )
        max_part = "Antworte in maximal " + max_part.strip(", ") + ". " if max_part else ""

        prompt = (
            f"Antworte in {language_normalized}, unabhängig von der Sprache des Quelltexts. "
            + max_part
            + "Fasse den folgenden Text prägnant und sachlich zusammen. "
            + "Erhalte die wichtigsten Informationen und den Kontext:\n\n"
            + source_text
        )

        result = await self.generate_text(prompt, DEFAULT_SYSTEM_PROMPT)
        LOGGER.debug("Summarization completed (output_chars=%s)", len(result))
        return result

    @staticmethod
    def _extract_text(response: litellm.ModelResponse) -> str:
        """Extract plain text content from a provider response object.

        Args:
            response: Raw LiteLLM provider response object.

        Returns:
            Extracted plain-text output.

        Raises:
            LLMResponseParseError: If expected response fields are missing or empty.

        Notes:
            This parser only supports non-streaming chat-completion style responses.
            If additional provider response schemas are needed, extend this method.
        """
        if not isinstance(response, litellm.ModelResponse):
            raise LLMResponseParseError(
                f"Unexpected provider response type: {type(response).__name__}"
            )

        # Intentionally restricted to non-streaming completion objects.
        # Stream responses like "chat.completion.chunk" are handled as unsupported.
        if response.object not in ("chat.completion", "model.completion"):
            raise LLMResponseParseError(
                f"Unexpected provider response object type: {response.object}"
            )
        choices: list[litellm.Choices] = response.choices  # type: ignore[assignment]
        LOGGER.debug("Extracting text from provider response (choices_count=%s)", len(choices))

        if not choices:
            raise LLMResponseParseError("provider response did not contain choices")
        message: litellm.Message = choices[0].message

        content: str | None = message.content
        if content is None or (isinstance(content, str) and not content.strip()):
            raise LLMResponseParseError("provider response message did not contain content")
        return content.strip()

    @staticmethod
    def _require_non_empty_text(value: str, field_name: str) -> str:
        """Validate a string input and return its stripped non-empty value.

        Args:
            value: Input string to validate.
            field_name: Field name used in validation error messages.

        Returns:
            Stripped non-empty string.

        Raises:
            ValueError: If input is not a string or is empty after stripping.
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty")
        return normalized

    @staticmethod
    def _validate_api_key(api_key: str | None) -> str | None:
        """Validate and normalize an optional API key.

        Args:
            api_key: Explicit API key override.

        Returns:
            Stripped API key if provided; `None` when no explicit key is configured
            (including empty/whitespace or non-string input).
        """
        if api_key is None:
            return None
        if not isinstance(api_key, str):
            LOGGER.warning(
                "API key is not a string (type=%s). Treating as no API key.",
                type(api_key).__name__,
            )
            return None
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            LOGGER.info("API key is empty or whitespace. Treating as no API key configured.")
            return None
        return normalized_api_key

    @staticmethod
    def _normalize_positive_count(name: str, value: object) -> int | None:
        """Normalize optional size limits to positive integers.

        Args:
            name: Parameter name used for logging.
            value: Raw user-provided value.

        Returns:
            Positive integer value, or `None` when value is missing/invalid.
        """
        if value is None:
            return None

        if isinstance(value, bool):
            LOGGER.warning("%s must be a positive integer. Ignoring value: %r", name, value)
            return None

        if isinstance(value, (int, float)):
            if value > 0:
                if isinstance(value, float):
                    LOGGER.debug("%s received float=%r, truncating to int", name, value)
                return int(value)

        LOGGER.warning("%s must be a positive integer. Ignoring value: %r", name, value)
        return None

    @staticmethod
    def _validate_timeout_seconds(timeout_seconds: object) -> float:
        """Validate and normalize per-request timeout.

        Args:
            timeout_seconds: Timeout in seconds.

        Returns:
            Validated timeout. Invalid values are replaced by
            `REQUEST_TIMEOUT_SECONDS`.
        """
        if isinstance(timeout_seconds, bool):
            LOGGER.warning(
                "timeout_seconds must be a positive number. Using default timeout=%.1fs instead of %r.",
                REQUEST_TIMEOUT_SECONDS,
                timeout_seconds,
            )
            return REQUEST_TIMEOUT_SECONDS

        if not isinstance(timeout_seconds, (int, float)):
            LOGGER.warning(
                "timeout_seconds must be a positive number. Using default timeout=%.1fs instead of %r.",
                REQUEST_TIMEOUT_SECONDS,
                timeout_seconds,
            )
            return REQUEST_TIMEOUT_SECONDS
        normalized_timeout = float(timeout_seconds)

        if not math.isfinite(normalized_timeout) or normalized_timeout <= 0:
            LOGGER.warning(
                "timeout_seconds must be a finite number greater than 0. "
                "Using default timeout=%.1fs instead of %r.",
                REQUEST_TIMEOUT_SECONDS,
                timeout_seconds,
            )
            return REQUEST_TIMEOUT_SECONDS

        return normalized_timeout

    @staticmethod
    def _validate_max_retries(max_retries: object) -> int:
        """Validate retry count configuration.

        Args:
            max_retries: Number of allowed retries.

        Returns:
            Validated retry count. Invalid values are replaced by `MAX_RETRIES`.

        Notes:
            Non-integer floats are truncated via `int(...)` (towards zero).
            Alternatives like rounding or always rounding up are intentionally
            not used here.
        """
        if isinstance(max_retries, bool):
            LOGGER.warning(
                "max_retries must be a non-negative integer. Using default max_retries=%s instead of %r.",
                MAX_RETRIES,
                max_retries,
            )
            return MAX_RETRIES

        if isinstance(max_retries, int):
            normalized_retries = max_retries
        elif isinstance(max_retries, float):
            if not math.isfinite(max_retries):
                LOGGER.warning(
                    "max_retries must be a finite non-negative integer. Using default max_retries=%s instead of %r.",
                    MAX_RETRIES,
                    max_retries,
                )
                return MAX_RETRIES
            if not max_retries.is_integer():
                LOGGER.warning(
                    "max_retries received float=%r, truncating to int.",
                    max_retries,
                )
            normalized_retries = int(max_retries)
        else:
            LOGGER.warning(
                "max_retries must be a non-negative integer. Using default max_retries=%s instead of %r.",
                MAX_RETRIES,
                max_retries,
            )
            return MAX_RETRIES

        if normalized_retries < 0:
            LOGGER.warning(
                "max_retries must be greater than or equal to 0. Using default max_retries=%s instead of %r.",
                MAX_RETRIES,
                max_retries,
            )
            return MAX_RETRIES

        return normalized_retries

    def _validate_retry_delay_constants(self) -> None:
        """Validate internal retry-delay constants.

        Raises:
            ValueError: If configured retry-delay constants are invalid.
        """
        if RETRY_BASE_DELAY_SECONDS <= 0:
            raise ValueError("retry_base_delay_seconds must be greater than 0")
        if RETRY_MAX_DELAY_SECONDS <= 0:
            raise ValueError("retry_max_delay_seconds must be greater than 0")
        if RETRY_BASE_DELAY_SECONDS > RETRY_MAX_DELAY_SECONDS:
            raise ValueError(
                "retry_base_delay_seconds must be less than or equal to retry_max_delay_seconds"
            )
        if RETRY_JITTER_MIN_SECONDS < 0:
            raise ValueError("RETRY_JITTER_MIN_SECONDS must be greater than or equal to 0")
        if RETRY_JITTER_MAX_SECONDS < RETRY_JITTER_MIN_SECONDS:
            raise ValueError(
                "RETRY_JITTER_MAX_SECONDS must be greater than or equal to RETRY_JITTER_MIN_SECONDS"
            )

    def _map_provider_exception(self, error: Exception) -> LLMProviderError:
        """Map a LiteLLM/provider exception to connector-specific error types."""
        status_code = getattr(error, "status_code", None)

        if isinstance(error, litellm.BudgetExceededError):
            return LLMQuotaExceededError("provider budget or quota exceeded")

        if isinstance(
            error, (litellm.AuthenticationError, litellm.PermissionDeniedError)
        ) or status_code in (401, 403):
            return LLMAuthenticationError("provider authentication or authorization failed")
        if isinstance(error, litellm.RateLimitError) or status_code == 429:
            return LLMRateLimitError("provider rate limit exceeded")

        if isinstance(
            error,
            (
                litellm.Timeout,
                litellm.APIConnectionError,
                litellm.InternalServerError,
                litellm.ServiceUnavailableError,
                litellm.BadGatewayError,
            ),
        ) or (isinstance(status_code, int) and 500 <= status_code < 600):
            return LLMTemporaryProviderError("provider request failed temporarily")

        return LLMProviderError("provider request failed")

    def _compute_retry_delay(self, attempt: int) -> float:
        """Compute exponential backoff with additive jitter.

        Args:
            attempt: Zero-based retry attempt index.

        Returns:
            Retry delay in seconds.
        """
        delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
        capped_delay = float(min(delay, RETRY_MAX_DELAY_SECONDS))
        jitter = random.uniform(RETRY_JITTER_MIN_SECONDS, RETRY_JITTER_MAX_SECONDS)
        total_delay = capped_delay + jitter
        LOGGER.debug(
            "Computed retry delay (attempt=%s, capped_delay=%.2fs, jitter=%.2fs, total=%.2fs)",
            attempt + 1,
            capped_delay,
            jitter,
            total_delay,
        )
        return total_delay
