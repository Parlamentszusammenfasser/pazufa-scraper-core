"""Provider-agnostic async connector for LLM text generation, summarization,
and structured data extraction.

Example — free-text generation:
    ```python
    import asyncio
    from collector_core.llm import LLMConnector

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

Example — structured extraction:
    ```python
    import asyncio
    from pydantic import BaseModel
    from collector_core.llm import LLMConnector

    class Keywords(BaseModel):
        sachgebiete: list[str]
        schlagworte: list[str]

    async def main() -> None:
        connector = LLMConnector(model="openai/gpt-4o-mini", temperature=0.1)
        result = await connector.extract(
            prompt="Extrahiere Schlagworte aus diesem Text: ...",
            response_model=Keywords,
        )
        print(result.sachgebiete, result.schlagworte)

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
from typing import Any, Final, TypeVar

import instructor
import litellm
from instructor.core import InstructorRetryException
from pydantic import BaseModel

from .models import SectionExtractionResult
from .prompts import SECTION_EXTRACTION_PROMPT

T = TypeVar("T", bound=BaseModel)

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


class LLMValidationError(LLMConnectorError):
    """Raised when the model cannot produce output matching the response schema."""


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
                Lower values are usually more deterministic. Invalid values are
                treated like `None`.
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
        self.temperature: float | None = self._validate_temperature(temperature)
        self.timeout_seconds: float = self._validate_timeout_seconds(timeout_seconds)
        self.max_retries: int = self._validate_max_retries(max_retries)
        self._validate_retry_delay_constants()
        self._rate_limiter: RateLimiter | None = self._initialize_rate_limiter(
            rate_limit_max_calls=rate_limit_max_calls,
            rate_limit_window_seconds=rate_limit_window_seconds,
        )
        self._instructor_client = instructor.from_litellm(
            litellm.acompletion, mode=instructor.Mode.TOOLS
        )
        LOGGER.debug("Initialized Instructor client (mode=TOOLS)")

        LOGGER.info(
            "Initialized LLMConnector (model=%s, api_key_set=%s, "
            "rate_limit_enabled=%s, timeout=%.1fs, max_retries=%s)",
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

        messages: list[dict[str, str]] = [
            {"role": "user", "content": normalized_prompt}
        ]
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
                LOGGER.debug(
                    "Waiting for local rate limiter slot (attempt=%s)", attempt + 1
                )
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
                    "Provider call failed (attempt=%s/%s, error_type=%s, "
                    "mapped_error_type=%s) %s",
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
                    "Provider request failed without retry (attempt=%s/%s, "
                    "error_type=%s)",
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
                f"Response type `CustomStreamWrapper` is not supported. "
                f"Got: {type(response).__name__}"
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
            character_count: Optional upper bound for character count. Invalid values
                are ignored.

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
            language_normalized = self._require_non_empty_text(
                language, field_name="language"
            )
        except ValueError:
            LOGGER.warning(
                "Empty input language for summarization; using default language "
                "(Deutsch)"
            )
            language_normalized = "Deutsch"

        sentences_count = self._normalize_positive_count(
            "sentences_count", sentences_count
        )
        word_count = self._normalize_positive_count("word_count", word_count)
        character_count = self._normalize_positive_count(
            "character_count", character_count
        )
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
        max_part = (
            "Antworte in maximal " + max_part.strip(", ") + ". " if max_part else ""
        )

        prompt = (
            f"Antworte in {language_normalized}, unabhängig von der Sprache des "
            + "Quelltexts. "
            + max_part
            + "Fasse den folgenden Text prägnant und sachlich zusammen. "
            + "Erhalte die wichtigsten Informationen und den Kontext:\n\n"
            + source_text
        )

        result = await self.generate_text(prompt, DEFAULT_SYSTEM_PROMPT)
        LOGGER.debug("Summarization completed (output_chars=%s)", len(result))
        return result

    async def extract(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = DEFAULT_SYSTEM_PROMPT,
        validation_retries: int = 2,
        validation_context: dict[str, object] | None = None,
    ) -> T:
        """Extract structured data from text using the configured model.

        Uses `Instructor <https://python.useinstructor.com/>`_ on top of
        LiteLLM to coerce model output into *response_model*.

        Args:
            prompt: User input prompt describing what to extract.
            response_model: Pydantic ``BaseModel`` subclass that defines the
                expected output schema.
            system_prompt: Optional system-level instruction. Behaves
                identically to :meth:`generate_text`.
            validation_retries: How many times Instructor may re-prompt the
                model when its output fails Pydantic validation. This is
                separate from the network-level retry controlled by
                ``max_retries``.
            validation_context: Optional dict passed to Pydantic's
                ``model_validate`` as context, allowing model validators
                to access runtime information (e.g. valid line ranges).

        Returns:
            A validated instance of *response_model*.

        Raises:
            ValueError: If *prompt* is empty/invalid, *response_model* is not
                a ``BaseModel`` subclass, or *validation_retries* is negative.
            LLMValidationError: If the model cannot produce valid output after
                all validation retries.
            LLMProviderError: If the provider call fails and cannot be
                recovered by retries.
        """
        normalized_prompt = self._require_non_empty_text(prompt, field_name="prompt")

        if not isinstance(response_model, type) or not issubclass(
            response_model, BaseModel
        ):
            raise ValueError("response_model must be a Pydantic BaseModel subclass")

        if not isinstance(validation_retries, int) or isinstance(
            validation_retries, bool
        ):
            raise ValueError("validation_retries must be a non-negative integer")
        if validation_retries < 0:
            raise ValueError("validation_retries must be a non-negative integer")

        normalized_system_prompt: str | None = None
        if system_prompt is not None:
            if not isinstance(system_prompt, str):
                raise ValueError("system_prompt must be a string or None")
            stripped_system_prompt = system_prompt.strip()
            if stripped_system_prompt:
                normalized_system_prompt = stripped_system_prompt

        messages: list[dict[str, str]] = [
            {"role": "user", "content": normalized_prompt}
        ]
        if normalized_system_prompt is not None:
            messages.insert(0, {"role": "system", "content": normalized_system_prompt})

        client = self._instructor_client

        LOGGER.debug(
            "Starting structured extraction (model=%s, response_model=%s, "
            "prompt_chars=%s, validation_retries=%s, network_retries=%s)",
            self.model,
            response_model.__name__,
            len(normalized_prompt),
            validation_retries,
            self.max_retries,
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            if self._rate_limiter is not None:
                LOGGER.debug(
                    "Waiting for local rate limiter slot (attempt=%s)", attempt + 1
                )
                await self._rate_limiter.acquire_slot()

            try:
                LOGGER.debug(
                    "Calling Instructor (attempt=%s/%s, timeout=%.1fs)",
                    attempt + 1,
                    self.max_retries + 1,
                    self.timeout_seconds,
                )
                result = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.model,
                        api_key=self.api_key,
                        messages=messages,
                        response_model=response_model,
                        temperature=self.temperature,
                        timeout=self.timeout_seconds,
                        max_retries=validation_retries,
                        validation_context=validation_context,
                    ),
                    self.timeout_seconds + 0.5,
                )
                LOGGER.debug(
                    "Structured extraction successful (attempt=%s/%s)",
                    attempt + 1,
                    self.max_retries + 1,
                )
                return result  # type: ignore[no-any-return]
            except InstructorRetryException as exc:
                raise LLMValidationError(
                    f"Model could not produce valid {response_model.__name__} "
                    f"after {validation_retries} validation retries"
                ) from exc
            except (asyncio.TimeoutError, litellm.exceptions.Timeout) as exc:
                mapped_error: LLMProviderError = LLMTemporaryProviderError(
                    "provider request timed out"
                )
                last_error = exc
                LOGGER.warning(
                    "Provider timeout (attempt=%s/%s, timeout=%.1fs)",
                    attempt + 1,
                    self.max_retries + 1,
                    self.timeout_seconds,
                )
            except Exception as exc:
                mapped_error = self._map_provider_exception(exc)
                last_error = exc
                LOGGER.warning(
                    "Provider call failed (attempt=%s/%s, error_type=%s, "
                    "mapped_error_type=%s) %s",
                    attempt + 1,
                    self.max_retries + 1,
                    type(exc).__name__,
                    type(mapped_error).__name__,
                    str(exc),
                )

            should_retry = attempt < self.max_retries and isinstance(
                mapped_error, (LLMRateLimitError, LLMTemporaryProviderError)
            )
            if not should_retry:
                LOGGER.error(
                    "Extraction failed without retry (attempt=%s/%s, error_type=%s)",
                    attempt + 1,
                    self.max_retries + 1,
                    type(mapped_error).__name__,
                )
                raise mapped_error from last_error

            backoff_seconds = self._compute_retry_delay(attempt)
            LOGGER.info(
                "Retrying extraction in %.2fs (next_attempt=%s/%s, error_type=%s)",
                backoff_seconds,
                attempt + 2,
                self.max_retries + 1,
                type(mapped_error).__name__,
            )
            await asyncio.sleep(backoff_seconds)

        raise LLMConnectorError("unreachable retry loop state")

    async def extract_relevant_section(
        self,
        text: str,
        vorgang_titel: str,
        vorgang_vnr: str | None = None,
        chunk_size: int = 30_000,
        chunk_overlap: int = 1_000,
        early_stop_after: int = 0,
    ) -> str | None:
        """Extract sections relevant to a Vorgang from a document.

        The document is split into overlapping chunks (or treated as a single
        chunk when short enough); for each chunk an LLM identifies relevant
        line ranges, and the corresponding text is extracted computationally
        (guaranteeing verbatim output).

        Args:
            text: Full document text (e.g. a parliamentary protocol).
            vorgang_titel: Title of the Vorgang to search for.
            vorgang_vnr: Optional Drucksache/Vorgangsnummer for context.
            chunk_size: Target chunk size in tokens for splitting.  This
                budget covers text lines only; the ~300-token extraction
                prompt is added on top.  The default (30 000) leaves ample
                headroom for typical model context windows.
            chunk_overlap: Overlap between consecutive chunks in tokens.
            early_stop_after: Once relevant content has been found, stop
                after this many consecutive irrelevant chunks.  Set to
                ``0`` to disable early stopping.  Chunks before the first
                relevant hit are always processed.

        Returns:
            The concatenated relevant sections, or ``None`` if no relevant
            content was found.

        Raises:
            ValueError: If *text* or *vorgang_titel* is empty/invalid.
            LLMProviderError: If a provider call fails.
            LLMValidationError: If the model cannot produce valid output.
        """
        normalized_text = self._require_non_empty_text(text, field_name="text")
        normalized_titel = self._require_non_empty_text(
            vorgang_titel, field_name="vorgang_titel"
        )

        source_lines = normalized_text.splitlines()
        chunks = self._chunk_lines(source_lines, chunk_size, chunk_overlap)
        LOGGER.info(
            "Split document into %s chunks (chunk_size=%s, overlap=%s)",
            len(chunks),
            chunk_size,
            chunk_overlap,
        )

        vorgang_vnr_part = f" (Drucksache {vorgang_vnr})" if vorgang_vnr else ""

        all_line_indices: set[int] = set()
        found_relevant = False
        consecutive_irrelevant = 0

        for chunk_idx, (start_line, end_line) in enumerate(chunks):
            if (
                early_stop_after > 0
                and found_relevant
                and consecutive_irrelevant >= early_stop_after
            ):
                LOGGER.info(
                    "Early stopping after %s consecutive irrelevant chunks "
                    "following relevant content (chunk %s/%s)",
                    consecutive_irrelevant,
                    chunk_idx + 1,
                    len(chunks),
                )
                break

            numbered_text = self._number_lines(source_lines, start_line, end_line)
            prompt = SECTION_EXTRACTION_PROMPT.format(
                vorgang_titel=normalized_titel,
                vorgang_vnr_part=vorgang_vnr_part,
                text=numbered_text,
            )

            LOGGER.debug(
                "Processing chunk %s/%s (lines %s-%s)",
                chunk_idx + 1,
                len(chunks),
                start_line + 1,
                end_line,
            )

            result: SectionExtractionResult = await self.extract(
                prompt=prompt,
                response_model=SectionExtractionResult,
                system_prompt=None,
                validation_context={
                    "min_line": start_line + 1,
                    "max_line": end_line,
                },
            )

            if not result.is_relevant or not result.relevant_lines:
                consecutive_irrelevant += 1
                LOGGER.debug(
                    "Chunk %s/%s: not relevant (consecutive=%s)",
                    chunk_idx + 1,
                    len(chunks),
                    consecutive_irrelevant,
                )
                continue

            found_relevant = True
            consecutive_irrelevant = 0

            for lr in result.relevant_lines:
                all_line_indices.update(range(lr.start - 1, lr.end))

        if not all_line_indices:
            LOGGER.info("No relevant content found in any chunk")
            return None

        unique_indices = sorted(all_line_indices)
        parts: list[str] = []
        for pos, idx in enumerate(unique_indices):
            if pos > 0 and idx != unique_indices[pos - 1] + 1:
                parts.append("")  # blank line between non-consecutive sections
            parts.append(source_lines[idx])
        extracted = "\n".join(parts)
        LOGGER.info(
            "Extracted %s lines from %s total",
            len(unique_indices),
            len(source_lines),
        )
        return extracted

    def _chunk_lines(
        self,
        lines: list[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[tuple[int, int]]:
        """Split lines into overlapping chunks by token budget.

        Each chunk is represented as a ``(start_index, end_index)`` tuple
        (0-based, end exclusive) into *lines*.

        Note:
            *chunk_size* covers only the text lines, not the surrounding
            prompt template.  Callers should account for prompt overhead
            when choosing *chunk_size* (the default of 30 000 leaves ample
            headroom for the ~300-token extraction prompt).

        Args:
            lines: Source text split into lines.
            chunk_size: Target token budget per chunk (text lines only,
                excluding prompt overhead).
            chunk_overlap: Overlap budget in tokens.

        Returns:
            List of ``(start, end)`` index tuples.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        total = len(lines)
        if total == 0:
            return []

        # Pre-compute per-line token counts to avoid redundant tokenizer calls.
        line_token_counts = [
            litellm.token_counter(model=self.model, text=line) for line in lines
        ]

        chunks: list[tuple[int, int]] = []
        start = 0

        while start < total:
            token_count = 0
            end = start
            while end < total:
                if token_count + line_token_counts[end] > chunk_size and end > start:
                    break
                token_count += line_token_counts[end]
                end += 1

            chunks.append((start, end))

            if end >= total:
                break

            overlap_tokens = 0
            overlap_start = end
            while overlap_start > start:
                if (
                    overlap_tokens + line_token_counts[overlap_start - 1]
                    > chunk_overlap
                ):
                    break
                overlap_tokens += line_token_counts[overlap_start - 1]
                overlap_start -= 1

            # Ensure forward progress: if the overlap backed up to or before
            # the current chunk start, advance by at least one line to avoid
            # an infinite loop (can happen when a single line exceeds
            # chunk_size, causing a very short chunk).
            start = max(overlap_start, start + 1)

        return chunks

    @staticmethod
    def _number_lines(lines: list[str], start: int, end: int) -> str:
        """Add ``[N]`` line number prefixes to a slice of lines.

        Line numbers are 1-based (matching what the LLM sees and returns).

        Args:
            lines: Full list of source lines.
            start: Start index (0-based, inclusive).
            end: End index (0-based, exclusive).

        Returns:
            Numbered text block.
        """
        return "\n".join(f"[{i + 1}] {lines[i]}" for i in range(start, end))

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
        LOGGER.debug(
            "Extracting text from provider response (choices_count=%s)", len(choices)
        )

        if not choices:
            raise LLMResponseParseError("provider response did not contain choices")
        message: litellm.Message = choices[0].message

        content: str | None = message.content
        if content is None or (isinstance(content, str) and not content.strip()):
            raise LLMResponseParseError(
                "provider response message did not contain content"
            )
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
            LOGGER.info(
                "API key is empty or whitespace. Treating as no API key configured."
            )
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
            LOGGER.warning(
                "%s must be a positive integer. Ignoring value: %r", name, value
            )
            return None

        if isinstance(value, (int, float)):
            if value > 0:
                if isinstance(value, float):
                    LOGGER.debug("%s received float=%r, truncating to int", name, value)
                return int(value)

        LOGGER.warning("%s must be a positive integer. Ignoring value: %r", name, value)
        return None

    @staticmethod
    def _validate_temperature(temperature: object) -> float | None:
        """Validate and normalize optional generation temperature.

        Args:
            temperature: Temperature override for provider generation.

        Returns:
            Normalized temperature, or `None` for missing/invalid values.
        """
        if temperature is None:
            return None
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            LOGGER.warning(
                "temperature must be a finite number. Treating %r as no explicit "
                "temperature.",
                temperature,
            )
            return None

        try:
            normalized_temperature = float(temperature)
        except OverflowError:
            LOGGER.warning(
                "temperature is out of range (type=%s). Treating it as no explicit "
                "temperature.",
                type(temperature).__name__,
            )
            return None
        if not math.isfinite(normalized_temperature):
            LOGGER.warning(
                "temperature must be a finite number. Treating %r as no explicit "
                "temperature.",
                temperature,
            )
            return None
        return normalized_temperature

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
                "timeout_seconds must be a positive number. Using default timeout="
                "%.1fs instead of %r.",
                REQUEST_TIMEOUT_SECONDS,
                timeout_seconds,
            )
            return REQUEST_TIMEOUT_SECONDS

        if not isinstance(timeout_seconds, (int, float)):
            LOGGER.warning(
                "timeout_seconds must be a positive number. Using default timeout="
                "%.1fs instead of %r.",
                REQUEST_TIMEOUT_SECONDS,
                timeout_seconds,
            )
            return REQUEST_TIMEOUT_SECONDS
        try:
            normalized_timeout = float(timeout_seconds)
        except OverflowError:
            LOGGER.warning(
                "timeout_seconds is out of range (type=%s). Using default "
                "timeout=%.1fs.",
                type(timeout_seconds).__name__,
                REQUEST_TIMEOUT_SECONDS,
            )
            return REQUEST_TIMEOUT_SECONDS

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
                "max_retries must be a non-negative integer. Using default max_retries="
                "%s instead of %r.",
                MAX_RETRIES,
                max_retries,
            )
            return MAX_RETRIES

        if isinstance(max_retries, int):
            normalized_retries = max_retries
        elif isinstance(max_retries, float):
            if not math.isfinite(max_retries):
                LOGGER.warning(
                    "max_retries must be a finite non-negative integer. Using default "
                    "max_retries=%s instead of %r.",
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
                "max_retries must be a non-negative integer. Using default max_retries="
                "%s instead of %r.",
                MAX_RETRIES,
                max_retries,
            )
            return MAX_RETRIES

        if normalized_retries < 0:
            LOGGER.warning(
                "max_retries must be greater than or equal to 0. Using default "
                "max_retries=%s instead of %r.",
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
                "retry_base_delay_seconds must be less than or equal to "
                "retry_max_delay_seconds"
            )
        if RETRY_JITTER_MIN_SECONDS < 0:
            raise ValueError(
                "RETRY_JITTER_MIN_SECONDS must be greater than or equal to 0"
            )
        if RETRY_JITTER_MAX_SECONDS < RETRY_JITTER_MIN_SECONDS:
            raise ValueError(
                "RETRY_JITTER_MAX_SECONDS must be greater than or equal to "
                "RETRY_JITTER_MIN_SECONDS"
            )

    def _map_provider_exception(self, error: Exception) -> LLMProviderError:
        """Map a LiteLLM/provider exception to connector-specific error types."""
        status_code = getattr(error, "status_code", None)

        if isinstance(error, litellm.BudgetExceededError):
            return LLMQuotaExceededError("provider budget or quota exceeded")

        if isinstance(
            error, (litellm.AuthenticationError, litellm.PermissionDeniedError)
        ) or status_code in (401, 403):
            return LLMAuthenticationError(
                "provider authentication or authorization failed"
            )
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
            "Computed retry delay (attempt=%s, capped_delay=%.2fs, jitter=%.2fs, "
            "total=%.2fs)",
            attempt + 1,
            capped_delay,
            jitter,
            total_delay,
        )
        return total_delay
