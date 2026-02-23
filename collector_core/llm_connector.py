"""Provider-agnostic async connector for LLM text generation and summarization.

Example:
    ```python
    import asyncio
    from collector_core.llm_connector import LLMConnector

    async def main() -> None:
        connector = LLMConnector(model="openai/gpt-4o-mini", temperature=0.1)
        summary = await connector.summarize(
            "Langer Quelltext fuer die Zusammenfassung ...",
            max_sentences=4,
            language="Deutsch",
        )
        print(summary)

    asyncio.run(main())
    ```
"""

from __future__ import annotations

import asyncio
import logging
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
    "Du bist ein präziser Assistent politische und juristische Texte. "
    "Antworte klar, faktenorientiert. "
    "Füge keine Foratierungen oder Hervorhebungen hinzu. " 
    "Antworte nur mit dem reinen Text, ohne Einleitungen oder Erklärungen. "
    "Die Antwort darf nur die direkt angeforderten Informationen enthalten. "
    "Spekulationen oder Annahmen sind zu vermeiden."
)


class LLMConnectorError(RuntimeError):
    """Raised when a provider response cannot be parsed as text."""


class LLMProviderError(LLMConnectorError):
    """Raised when the LLM provider returns a known request/response failure."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when provider authentication fails (e.g., invalid or missing API key)."""


class LLMQuotaExceededError(LLMProviderError):
    """Raised when provider quota/budget is exhausted."""


class LLMRateLimitError(LLMProviderError):
    """Raised when provider-side rate limits are exceeded."""


class LLMTemporaryProviderError(LLMProviderError):
    """Raised for transient provider failures (timeout/5xx)."""


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

        self.max_calls: int = int(max_calls)
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
    """Thin provider-agnostic connector for async text generation via LiteLLM."""

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
            timeout_seconds: Timeout per provider call in seconds.
            max_retries: Number of retry attempts for retryable provider errors.

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

    async def generate_text(self, prompt: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
        """Generate text using the configured model.

        Args:
            prompt: User input prompt for the model.
            system_prompt: System-level instruction for model behavior.

        Returns:
            The generated plain-text model output.

        Raises:
            ValueError: If prompt/system prompt validation fails.
            LLMProviderError: If provider call fails and cannot be recovered by retries.
            LLMConnectorError: If provider response structure cannot be parsed.
        """
        request_kwargs = self._build_request(prompt=prompt, system_prompt=system_prompt)
        prompt_length = len(request_kwargs["messages"][1]["content"])
        LOGGER.debug(
            "Starting text generation (model=%s, prompt_chars=%s, retries=%s)",
            self.model,
            prompt_length,
            self.max_retries,
        )

        for attempt in range(self.max_retries + 1):
            if self._rate_limiter is not None:
                LOGGER.debug("Waiting for local rate-limiter slot (attempt=%s)", attempt + 1)
                await self._rate_limiter.acquire_slot()

            try:
                LOGGER.debug(
                    "Calling provider (attempt=%s/%s, timeout=%.1fs)",
                    attempt + 1,
                    self.max_retries + 1,
                    self.timeout_seconds,
                )
                response = await asyncio.wait_for(
                    litellm.acompletion(**request_kwargs, api_key=self.api_key), timeout=self.timeout_seconds
                )
                LOGGER.debug(
                    "Provider call successful (attempt=%s/%s)",
                    attempt + 1,
                    self.max_retries + 1,
                )
                return self._extract_text(response)
            except asyncio.TimeoutError as exc:
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
                LOGGER.warning(
                    "Provider call failed (attempt=%s/%s, error_type=%s) %s",
                    attempt + 1,
                    self.max_retries + 1,
                    type(exc).__name__,
                    str(exc),
                )
                mapped_error: LLMProviderError = LLMTemporaryProviderError(
                    "provider request failed"
                )
                original_error: Exception = exc

            should_retry: bool = attempt < self.max_retries and self._is_retryable_error(
                mapped_error
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

        raise LLMConnectorError("unreachable retry loop state")

    def _build_request(self, prompt: str, system_prompt: str) -> dict[str, Any]:
        """Build a LiteLLM chat request payload from validated prompt data.

        Args:
            prompt: User prompt.
            system_prompt: System instruction prompt.

        Returns:
            A LiteLLM-compatible request payload.

        Raises:
            ValueError: If prompt or system prompt is empty/invalid.
        """
        user_prompt = self._require_non_empty_text(prompt, field_name="prompt")
        normalized_system_prompt = self._require_non_empty_text(
            system_prompt, field_name="system_prompt"
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": normalized_system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

    async def summarize(self, text: str, max_sentences: int = 5, language: str = "Deutsch") -> str:
        """Create a concise summary for an input text.

        Args:
            text: Source text to summarize.
            max_sentences: Maximum sentence count for the summary.
            language: Target language for the summary output.

        Returns:
            A concise generated summary.

        Raises:
            ValueError: If input validation fails.
            LLMProviderError: If provider call fails and cannot be recovered by retries.
            LLMConnectorError: If provider response structure cannot be parsed.
        """
        source_text = self._require_non_empty_text(text, field_name="text")
        normalized_language = self._require_non_empty_text(language, field_name="language")
        if max_sentences <= 0:
            raise ValueError("max_sentences must be greater than 0")
        LOGGER.debug(
            "Starting summarization (language=%s, max_sentences=%s, input_chars=%s)",
            normalized_language,
            max_sentences,
            len(source_text),
        )

        prompt = (
            f"Fasse den folgenden Text in {normalized_language} zusammen. "
            f"Nenne nur die Kernaussagen in maximal {max_sentences} Sätzen.\n\n{source_text}"
        )
        result = await self.generate_text(prompt=prompt, system_prompt=DEFAULT_SYSTEM_PROMPT)
        LOGGER.debug("Summarization completed (output_chars=%s)", len(result))
        return result

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract plain text content from a provider response object.

        Args:
            response: Raw LiteLLM provider response object.

        Returns:
            Extracted plain-text output.

        Raises:
            LLMConnectorError: If expected response fields are missing or empty.
        """
        choices = LLMConnector._get_field(response, "choices")
        if not isinstance(choices, list) or not choices:
            raise LLMConnectorError("provider response did not contain choices")

        message = LLMConnector._get_field(choices[0], "message")
        content = LLMConnector._get_field(message, "content")
        text = LLMConnector._normalize_content(content)
        if not text:
            raise LLMConnectorError("provider response did not contain text content")
        return text

    @staticmethod
    def _normalize_content(content: Any) -> str:
        """Normalize provider content blocks into a single plain-text string.

        Args:
            content: Provider response `message.content` field.

        Returns:
            Normalized text representation.
        """
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    item_text = item.strip()
                    if item_text:
                        parts.append(item_text)
                    continue

                item_text = LLMConnector._get_field(item, "text")
                if isinstance(item_text, str):
                    cleaned = item_text.strip()
                    if cleaned:
                        parts.append(cleaned)
            return "\n".join(parts).strip()

        LOGGER.warning("Unexpected content type from provider: %s", type(content).__name__)
        return ""

    @staticmethod
    def _get_field(obj: Any, field: str) -> Any:
        """Read a named field from dict-like or attribute-based objects.

        Args:
            obj: Source object.
            field: Field name to read.

        Returns:
            Field value or `None` when absent.
        """
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

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
            LOGGER.warning("API key is not a string (type=%s). Treating as no API key.", type(api_key).__name__)
            return None
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            LOGGER.info("API key is empty or whitespace. Treating as no API key configured.")   
            return None
        return normalized_api_key

    @staticmethod
    def _validate_timeout_seconds(timeout_seconds: float) -> float:
        """Validate and normalize per-request timeout.

        Args:
            timeout_seconds: Timeout in seconds.

        Returns:
            Validated timeout.

        Raises:
            ValueError: If timeout is not greater than zero.
        """
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        return float(timeout_seconds)

    @staticmethod
    def _validate_max_retries(max_retries: int) -> int:
        """Validate retry count configuration.

        Args:
            max_retries: Number of allowed retries.

        Returns:
            Validated retry count.

        Raises:
            ValueError: If retry count is negative.
        """
        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")
        return max_retries

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

    @staticmethod
    def _is_retryable_error(error: LLMProviderError) -> bool:
        """Return whether an error type should trigger a retry attempt.

        Args:
            error: Mapped connector/provider error.

        Returns:
            `True` if retry logic should handle this error type, else `False`.
        """
        return isinstance(error, (LLMRateLimitError, LLMTemporaryProviderError))

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
