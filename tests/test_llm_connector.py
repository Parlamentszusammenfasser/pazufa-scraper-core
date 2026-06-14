from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from instructor.core import InstructorRetryException

from pazufa_corelib.llm.llm_connector import (
    TOKEN_ESTIMATE_OUTPUT_BUFFER,
    LLMAuthenticationError,
    LLMConnector,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTemporaryProviderError,
    LLMValidationError,
    RateLimiter,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class Keywords(BaseModel):
    sachgebiete: list[str]
    schlagworte: list[str]


class SpeakerInfo(BaseModel):
    name: str
    party: str = Field(description="Party abbreviation")


def _make_connector(**kwargs: object) -> LLMConnector:
    defaults: dict[str, object] = {
        "model": "openai/gpt-4o-mini",
        "rate_limit_max_calls": None,
        "max_retries": 3,
    }
    defaults.update(kwargs)
    with patch("instructor.from_provider", return_value=MagicMock()):
        return LLMConnector(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# extract() — input validation
# ---------------------------------------------------------------------------


class TestExtractInputValidation:
    """Verify that extract() rejects invalid inputs before calling the model."""

    def test_empty_prompt_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="prompt must not be empty"):
            asyncio.run(connector.extract(prompt="   ", response_model=Keywords))

    def test_non_string_prompt_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="prompt must be a string"):
            asyncio.run(connector.extract(prompt=42, response_model=Keywords))  # type: ignore[arg-type]

    def test_non_basemodel_response_model_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="response_model must be a Pydantic BaseModel"
        ):
            asyncio.run(connector.extract(prompt="test", response_model=dict))  # type: ignore[arg-type,type-var]

    def test_string_response_model_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="response_model must be a Pydantic BaseModel"
        ):
            asyncio.run(connector.extract(prompt="test", response_model="Keywords"))  # type: ignore[arg-type]

    def test_negative_validation_retries_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="validation_retries must be a non-negative integer"
        ):
            asyncio.run(
                connector.extract(
                    prompt="test", response_model=Keywords, validation_retries=-1
                )
            )

    def test_bool_validation_retries_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="validation_retries must be a non-negative integer"
        ):
            asyncio.run(
                connector.extract(
                    prompt="test",
                    response_model=Keywords,
                    validation_retries=True,  # type: ignore[arg-type]
                )
            )

    def test_non_string_system_prompt_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="system_prompt must be a string or None"):
            asyncio.run(
                connector.extract(
                    prompt="test",
                    response_model=Keywords,
                    system_prompt=123,  # type: ignore[arg-type]
                )
            )


# ---------------------------------------------------------------------------
# extract() — happy path
# ---------------------------------------------------------------------------


class TestExtractHappyPath:
    """Verify extract() returns a validated Pydantic model on success."""

    @pytest.mark.asyncio
    async def test_returns_validated_model(self) -> None:
        connector = _make_connector()
        expected = Keywords(sachgebiete=["Bildung"], schlagworte=["Schule", "Lehrer"])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=expected)
        connector._instructor_client = mock_client

        result = await connector.extract(
            prompt="Extrahiere Schlagworte",
            response_model=Keywords,
        )

        assert isinstance(result, Keywords)
        assert result.sachgebiete == ["Bildung"]
        assert result.schlagworte == ["Schule", "Lehrer"]

    @pytest.mark.asyncio
    async def test_passes_correct_kwargs_to_instructor(self) -> None:
        connector = _make_connector(temperature=0.1)
        expected = Keywords(sachgebiete=[], schlagworte=[])

        mock_client = MagicMock()
        mock_create = AsyncMock(return_value=expected)
        mock_client.chat.completions.create = mock_create
        connector._instructor_client = mock_client

        await connector.extract(
            prompt="test prompt",
            response_model=Keywords,
            system_prompt="Be precise.",
            validation_retries=3,
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o-mini"
        assert call_kwargs["response_model"] is Keywords
        assert call_kwargs["max_retries"] == 3
        assert call_kwargs["temperature"] == 0.1
        # System prompt should be first message
        assert call_kwargs["messages"][0] == {
            "role": "system",
            "content": "Be precise.",
        }
        assert call_kwargs["messages"][1] == {"role": "user", "content": "test prompt"}

    @pytest.mark.asyncio
    async def test_no_system_prompt(self) -> None:
        connector = _make_connector()
        expected = Keywords(sachgebiete=[], schlagworte=[])

        mock_client = MagicMock()
        mock_create = AsyncMock(return_value=expected)
        mock_client.chat.completions.create = mock_create
        connector._instructor_client = mock_client

        await connector.extract(
            prompt="test prompt",
            response_model=Keywords,
            system_prompt=None,
        )

        call_kwargs = mock_create.call_args[1]
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_zero_validation_retries(self) -> None:
        connector = _make_connector()
        expected = Keywords(sachgebiete=[], schlagworte=[])

        mock_client = MagicMock()
        mock_create = AsyncMock(return_value=expected)
        mock_client.chat.completions.create = mock_create
        connector._instructor_client = mock_client

        await connector.extract(
            prompt="test", response_model=Keywords, validation_retries=0
        )

        assert mock_create.call_args[1]["max_retries"] == 0


# ---------------------------------------------------------------------------
# extract() — validation failure → LLMValidationError
# ---------------------------------------------------------------------------


class TestExtractValidationFailure:
    """Verify Instructor validation failures map to LLMValidationError."""

    @pytest.mark.asyncio
    async def test_instructor_retry_exception_raises_validation_error(self) -> None:
        from instructor.core import InstructorRetryException

        connector = _make_connector()

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=InstructorRetryException(
                n_attempts=3,
                messages=[],
                last_completion=None,
                total_usage=MagicMock(),
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(
            LLMValidationError, match="could not produce valid Keywords"
        ):
            await connector.extract(prompt="test", response_model=Keywords)


# ---------------------------------------------------------------------------
# extract() — network retry behaviour
# ---------------------------------------------------------------------------


class TestExtractNetworkRetry:
    """Verify network-level retries work correctly for extract()."""

    @pytest.mark.asyncio
    async def test_retries_on_timeout_then_succeeds(self) -> None:
        connector = _make_connector(max_retries=2)
        expected = Keywords(sachgebiete=["Justiz"], schlagworte=["Urteil"])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                litellm.exceptions.Timeout(
                    message="timeout", model="test", llm_provider="openai"
                ),
                expected,
            ]
        )
        connector._instructor_client = mock_client

        with patch(
            "pazufa_corelib.llm.llm_connector.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await connector.extract(prompt="test", response_model=Keywords)

        assert result.sachgebiete == ["Justiz"]
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self) -> None:
        connector = _make_connector(max_retries=3)

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=litellm.AuthenticationError(
                message="Invalid API key",
                llm_provider="openai",
                model="gpt-4o-mini",
                response=MagicMock(status_code=401),
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMAuthenticationError):
            await connector.extract(prompt="test", response_model=Keywords)

        assert mock_client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        connector = _make_connector(max_retries=1)

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=litellm.exceptions.Timeout(
                message="timeout", model="test", llm_provider="openai"
            )
        )
        connector._instructor_client = mock_client

        with patch(
            "pazufa_corelib.llm.llm_connector.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(LLMTemporaryProviderError):
                await connector.extract(prompt="test", response_model=Keywords)

        assert mock_client.chat.completions.create.call_count == 2


# ---------------------------------------------------------------------------
# extract() — Instructor client init
# ---------------------------------------------------------------------------


class TestExtractInstructorInit:
    """Verify the Instructor client is initialized during __init__."""

    def test_instructor_client_set_after_init(self) -> None:
        connector = _make_connector()
        assert connector._instructor_client is not None


# ---------------------------------------------------------------------------
# summarize() — public API
# ---------------------------------------------------------------------------


from pazufa_corelib.llm.models import ZusammenfassungResult  # noqa: E402


class TestSummarize:
    """Verify summarize() delegates to extract(ZusammenfassungResult) correctly."""

    @pytest.mark.asyncio
    async def test_returns_zusammenfassung_string(self) -> None:
        connector = _make_connector()
        expected = (
            "Eine prägnante Zusammenfassung des Textes über die geplante "
            "Bildungsreform und ihre wesentlichen Maßnahmen."
        )

        with patch.object(
            connector,
            "extract",
            new_callable=AsyncMock,
            return_value=ZusammenfassungResult(zusammenfassung=expected),
        ):
            result = await connector.summarize(
                "Langer Quellentext über Bildungspolitik."
            )

        assert result == expected

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="text must not be empty"):
            await connector.summarize("   ")

    @pytest.mark.asyncio
    async def test_extract_called_with_zusammenfassung_model(self) -> None:
        connector = _make_connector()
        mock_extract = AsyncMock(
            return_value=ZusammenfassungResult(
                zusammenfassung=(
                    "Eine gültige Zusammenfassung des Quelltextes für den Test."
                )
            )
        )

        with patch.object(connector, "extract", mock_extract):
            await connector.summarize("Quellentext.")

        call_args = mock_extract.call_args
        assert call_args[0][1] is ZusammenfassungResult

    @pytest.mark.asyncio
    async def test_invalid_language_falls_back_to_deutsch(self) -> None:
        connector = _make_connector()
        captured: list[str] = []

        async def capture(
            prompt: str, response_model: type, **kwargs: object
        ) -> ZusammenfassungResult:
            captured.append(prompt)
            return ZusammenfassungResult(
                zusammenfassung="Eine gültige Zusammenfassung des Quelltextes für den Test."
            )

        with patch.object(connector, "extract", side_effect=capture):
            await connector.summarize("Quellentext.", language="   ")

        assert "Deutsch" in captured[0]

    @pytest.mark.asyncio
    async def test_length_limit_relaxes_minimum_via_context(self) -> None:
        """An explicit count limit forwards allow_short to the validator."""
        connector = _make_connector()
        mock_extract = AsyncMock(
            return_value=ZusammenfassungResult(
                zusammenfassung=(
                    "Eine gültige Zusammenfassung des Quelltextes für den Test."
                )
            )
        )

        with patch.object(connector, "extract", mock_extract):
            await connector.summarize("Quellentext.", word_count=5)

        assert mock_extract.call_args.kwargs["validation_context"] == {
            "allow_short": True
        }

    @pytest.mark.asyncio
    async def test_no_length_limit_keeps_floor(self) -> None:
        """Without a count limit no allow_short context is sent (floor applies)."""
        connector = _make_connector()
        mock_extract = AsyncMock(
            return_value=ZusammenfassungResult(
                zusammenfassung=(
                    "Eine gültige Zusammenfassung des Quelltextes für den Test."
                )
            )
        )

        with patch.object(connector, "extract", mock_extract):
            await connector.summarize("Quellentext.")

        assert mock_extract.call_args.kwargs["validation_context"] is None

    @pytest.mark.asyncio
    async def test_validation_error_propagates(self) -> None:
        connector = _make_connector()

        with patch.object(
            connector,
            "extract",
            new_callable=AsyncMock,
            side_effect=LLMValidationError(
                "could not produce valid ZusammenfassungResult"
            ),
        ):
            with pytest.raises(LLMValidationError):
                await connector.summarize("Quellentext.")

    @pytest.mark.asyncio
    async def test_provider_error_propagates(self) -> None:
        connector = _make_connector()

        with patch.object(
            connector,
            "extract",
            new_callable=AsyncMock,
            side_effect=LLMRateLimitError("rate limited"),
        ):
            with pytest.raises(LLMRateLimitError):
                await connector.summarize("Quellentext.")


# ---------------------------------------------------------------------------
# RateLimiter — basic behaviour
# ---------------------------------------------------------------------------


class TestRateLimiterBasic:
    """Verify basic RateLimiter request-count and construction behaviour."""

    def test_invalid_max_calls_raises(self) -> None:
        with pytest.raises(ValueError, match="max_calls must be an integer"):
            RateLimiter(max_calls="5", per_seconds=1.0)  # type: ignore[arg-type]

    def test_zero_max_calls_raises(self) -> None:
        with pytest.raises(ValueError, match="max_calls must be greater than 0"):
            RateLimiter(max_calls=0, per_seconds=1.0)

    def test_invalid_per_seconds_raises(self) -> None:
        with pytest.raises(ValueError, match="per_seconds must be a number"):
            RateLimiter(max_calls=5, per_seconds="abc")  # type: ignore[arg-type]

    def test_zero_per_seconds_raises(self) -> None:
        with pytest.raises(ValueError, match="per_seconds must be greater than 0"):
            RateLimiter(max_calls=5, per_seconds=0)

    def test_bool_max_calls_raises(self) -> None:
        with pytest.raises(ValueError, match="max_calls must be an integer"):
            RateLimiter(max_calls=True, per_seconds=1.0)

    @pytest.mark.asyncio
    async def test_grants_slots_up_to_max_calls(self) -> None:
        limiter = RateLimiter(max_calls=3, per_seconds=60.0)
        for _ in range(3):
            await limiter.acquire_slot()
        assert len(limiter._timestamps) == 3

    @pytest.mark.asyncio
    async def test_no_token_tracking_by_default(self) -> None:
        limiter = RateLimiter(max_calls=5, per_seconds=60.0)
        await limiter.acquire_slot(estimated_tokens=1000)
        # Token usage deque should remain empty when max_tokens is None
        assert len(limiter._token_usage) == 0


# ---------------------------------------------------------------------------
# RateLimiter — token budget (TPM)
# ---------------------------------------------------------------------------


class TestRateLimiterTokenBudget:
    """Verify token-based (TPM) rate limiting."""

    def test_invalid_max_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_tokens must be an integer"):
            RateLimiter(max_calls=5, per_seconds=1.0, max_tokens="1000")  # type: ignore[arg-type]

    def test_zero_max_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            RateLimiter(max_calls=5, per_seconds=1.0, max_tokens=0)

    def test_bool_max_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_tokens must be an integer"):
            RateLimiter(max_calls=5, per_seconds=1.0, max_tokens=True)

    def test_negative_max_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            RateLimiter(max_calls=5, per_seconds=1.0, max_tokens=-100)

    @pytest.mark.asyncio
    async def test_grants_slot_within_token_budget(self) -> None:
        limiter = RateLimiter(max_calls=10, per_seconds=60.0, max_tokens=30_000)
        await limiter.acquire_slot(estimated_tokens=10_000)
        assert len(limiter._token_usage) == 1
        assert limiter._token_usage[0][1] == 10_000

    @pytest.mark.asyncio
    async def test_tracks_cumulative_token_usage(self) -> None:
        limiter = RateLimiter(max_calls=10, per_seconds=60.0, max_tokens=30_000)
        await limiter.acquire_slot(estimated_tokens=10_000)
        await limiter.acquire_slot(estimated_tokens=15_000)
        assert len(limiter._token_usage) == 2

    @pytest.mark.asyncio
    async def test_blocks_when_token_budget_exceeded(self) -> None:
        """Second request should block when it would exceed the token budget."""
        limiter = RateLimiter(max_calls=10, per_seconds=60.0, max_tokens=30_000)
        await limiter.acquire_slot(estimated_tokens=25_000)

        # The next 25k request would push total to 50k > 30k, so it should wait.
        # We patch asyncio.sleep to avoid actually sleeping and verify it blocks.
        sleep_called = False
        original_sleep = asyncio.sleep

        async def mock_sleep(delay: float) -> None:
            nonlocal sleep_called
            sleep_called = True
            # Simulate time passing by expiring the old token entry.
            limiter._token_usage.clear()
            limiter._timestamps.clear()
            await original_sleep(0)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await limiter.acquire_slot(estimated_tokens=25_000)

        assert sleep_called

    @pytest.mark.asyncio
    async def test_zero_tokens_ignored_for_tracking(self) -> None:
        """Calls with estimated_tokens=0 should not create token usage entries."""
        limiter = RateLimiter(max_calls=10, per_seconds=60.0, max_tokens=30_000)
        await limiter.acquire_slot(estimated_tokens=0)
        assert len(limiter._token_usage) == 0

    @pytest.mark.asyncio
    async def test_none_max_tokens_ignores_token_estimates(self) -> None:
        """When max_tokens is None, estimated_tokens should be ignored entirely."""
        limiter = RateLimiter(max_calls=10, per_seconds=60.0, max_tokens=None)
        await limiter.acquire_slot(estimated_tokens=999_999)
        assert len(limiter._token_usage) == 0

    @pytest.mark.asyncio
    async def test_blocks_on_tokens_while_call_slots_available(self) -> None:
        """Token budget should block even when plenty of call slots remain."""
        limiter = RateLimiter(max_calls=100, per_seconds=60.0, max_tokens=10_000)
        # Use most of the token budget but only 1 of 100 call slots.
        await limiter.acquire_slot(estimated_tokens=9_000)
        assert len(limiter._timestamps) == 1  # plenty of call slots left

        sleep_called = False
        original_sleep = asyncio.sleep

        async def mock_sleep(delay: float) -> None:
            nonlocal sleep_called
            sleep_called = True
            # Simulate window expiry for tokens only.
            limiter._token_usage.clear()
            await original_sleep(0)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await limiter.acquire_slot(estimated_tokens=5_000)

        assert sleep_called, "Should have blocked on token budget, not call slots"


# ---------------------------------------------------------------------------
# LLMConnector — TPM configuration
# ---------------------------------------------------------------------------


class TestConnectorTPMConfig:
    """Verify LLMConnector passes TPM configuration to RateLimiter."""

    def test_max_tokens_passed_to_rate_limiter(self) -> None:
        connector = _make_connector(
            rate_limit_max_calls=10,
            rate_limit_max_tokens=30_000,
        )
        assert connector._rate_limiter is not None
        assert connector._rate_limiter.max_tokens == 30_000

    def test_max_tokens_none_by_default(self) -> None:
        connector = _make_connector(rate_limit_max_calls=10)
        assert connector._rate_limiter is not None
        assert connector._rate_limiter.max_tokens is None

    def test_invalid_max_tokens_disables_limiter(self) -> None:
        connector = _make_connector(
            rate_limit_max_calls=10,
            rate_limit_max_tokens=-5,
        )
        # Invalid max_tokens causes limiter init to fail gracefully
        assert connector._rate_limiter is None


# ---------------------------------------------------------------------------
# LLMConnector — token estimation
# ---------------------------------------------------------------------------


class TestEstimateRequestTokens:
    """Verify _estimate_request_tokens returns input tokens + output buffer."""

    def test_returns_zero_when_token_limiting_disabled(self) -> None:
        connector = _make_connector(rate_limit_max_calls=None)
        messages = [{"role": "user", "content": "Hello"}]
        assert connector._estimate_request_tokens(messages) == 0

    def test_returns_zero_when_max_tokens_is_none(self) -> None:
        connector = _make_connector(rate_limit_max_calls=10)
        messages = [{"role": "user", "content": "Hello"}]
        assert connector._estimate_request_tokens(messages) == 0

    def test_estimates_tokens_with_buffer(self) -> None:
        connector = _make_connector(
            rate_limit_max_calls=10,
            rate_limit_max_tokens=30_000,
        )
        messages = [
            {"role": "system", "content": "Be precise."},
            {"role": "user", "content": "Summarize this text."},
        ]

        with patch(
            "pazufa_corelib.llm.llm_connector.litellm.token_counter",
            side_effect=lambda model, text: len(text.split()),
        ):
            result = connector._estimate_request_tokens(messages)

        # "Be precise." = 2 words, "Summarize this text." = 3 words
        expected_input = 2 + 3
        assert result == expected_input + TOKEN_ESTIMATE_OUTPUT_BUFFER

    def test_returns_zero_when_token_counter_raises(self) -> None:
        """If litellm.token_counter raises, return 0 instead of propagating."""
        connector = _make_connector(
            rate_limit_max_calls=10,
            rate_limit_max_tokens=30_000,
        )
        messages = [{"role": "user", "content": "Hello"}]

        with patch(
            "pazufa_corelib.llm.llm_connector.litellm.token_counter",
            side_effect=Exception("unsupported model"),
        ):
            result = connector._estimate_request_tokens(messages)

        assert result == 0

    def test_handles_missing_content_key(self) -> None:
        """Messages without a 'content' key should not raise."""
        connector = _make_connector(
            rate_limit_max_calls=10,
            rate_limit_max_tokens=30_000,
        )
        messages: list[dict[str, str]] = [
            {"role": "assistant"},
            {"role": "user", "content": "Hello"},
        ]

        with patch(
            "pazufa_corelib.llm.llm_connector.litellm.token_counter",
            side_effect=lambda model, text: len(text.split()) if text else 0,
        ):
            result = connector._estimate_request_tokens(messages)

        # "" (empty fallback) = 0 words, "Hello" = 1 word
        assert result == 1 + TOKEN_ESTIMATE_OUTPUT_BUFFER

    def test_token_counter_failure_logs_at_error_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Token counter failure should be logged at ERROR, not WARNING."""
        import logging

        connector = _make_connector(
            rate_limit_max_calls=10,
            rate_limit_max_tokens=30_000,
        )
        messages = [{"role": "user", "content": "Hello"}]

        with patch(
            "pazufa_corelib.llm.llm_connector.litellm.token_counter",
            side_effect=Exception("unsupported model"),
        ):
            with caplog.at_level(
                logging.ERROR, logger="pazufa_corelib.llm.llm_connector"
            ):
                result = connector._estimate_request_tokens(messages)

        assert result == 0
        assert any(r.levelno == logging.ERROR for r in caplog.records)


# ---------------------------------------------------------------------------
# RateLimiter — acquire_slot with estimated_tokens exceeding max_tokens
# ---------------------------------------------------------------------------


class TestRateLimiterTokenExceedsBudget:
    """acquire_slot must raise immediately when estimated_tokens > max_tokens."""

    @pytest.mark.asyncio
    async def test_raises_when_single_request_exceeds_budget(self) -> None:
        """A request larger than the total token budget should raise ValueError."""
        limiter = RateLimiter(max_calls=100, per_seconds=60.0, max_tokens=1_000)
        with pytest.raises(ValueError, match="estimated_tokens.*exceeds max_tokens"):
            await limiter.acquire_slot(estimated_tokens=5_000)

    @pytest.mark.asyncio
    async def test_raises_on_empty_window_when_request_exceeds_budget(self) -> None:
        """Should also raise after the window has fully expired (empty _token_usage)."""
        limiter = RateLimiter(max_calls=100, per_seconds=60.0, max_tokens=2_000)
        # Manually drain the deque to simulate a fully-expired window.
        limiter._token_usage.clear()
        with pytest.raises(ValueError, match="estimated_tokens.*exceeds max_tokens"):
            await limiter.acquire_slot(estimated_tokens=2_001)

    @pytest.mark.asyncio
    async def test_exactly_at_budget_does_not_raise(self) -> None:
        """estimated_tokens == max_tokens is on the boundary and should be allowed."""
        limiter = RateLimiter(max_calls=100, per_seconds=60.0, max_tokens=5_000)
        # Should not raise — equal to budget is permitted.
        await limiter.acquire_slot(estimated_tokens=5_000)


# ---------------------------------------------------------------------------
# extract() — InstructorRetryException error classification
# ---------------------------------------------------------------------------


def _make_instructor_retry(
    failed_exceptions: list[Exception] | None = None,
    cause: Exception | None = None,
) -> "InstructorRetryException":
    """Build an InstructorRetryException with controlled failed_attempts."""
    from instructor.core import InstructorRetryException
    from instructor.core.exceptions import FailedAttempt

    failed_attempts = None
    if failed_exceptions is not None:
        failed_attempts = [
            FailedAttempt(
                attempt_number=i + 1,
                exception=exc,
                completion=None,
            )
            for i, exc in enumerate(failed_exceptions)
        ]

    # The real InstructorRetryException passes the last error as the first
    # positional arg (via tenacity's last_attempt._exception), so it ends up
    # in exc.args[0].  Replicate that here.
    last_exc = failed_exceptions[-1] if failed_exceptions else None
    exc = InstructorRetryException(
        last_exc,
        n_attempts=len(failed_exceptions) if failed_exceptions else 1,
        messages=[],
        last_completion=None,
        total_usage=MagicMock(),
        failed_attempts=failed_attempts,
    )
    if cause is not None:
        exc.__cause__ = cause
    return exc


class TestExtractErrorClassification:
    """Verify InstructorRetryException is correctly classified as either
    a validation error or a provider error based on failed_attempts."""

    @pytest.mark.asyncio
    async def test_rate_limit_in_retry_raises_rate_limit_error(self) -> None:
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[
                    litellm.RateLimitError("rate limited", "model", "provider")
                ],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMRateLimitError):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_auth_error_in_retry_raises_auth_error(self) -> None:
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[
                    litellm.AuthenticationError("bad key", "model", "provider")
                ],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMAuthenticationError):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_budget_error_in_retry_raises_quota_error(self) -> None:
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[
                    litellm.BudgetExceededError(current_cost=15.0, max_budget=10.0)
                ],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMQuotaExceededError):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_timeout_in_retry_raises_temporary_error(self) -> None:
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[litellm.Timeout("timed out", "model", "provider")],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMTemporaryProviderError):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_pure_validation_errors_still_raise_validation_error(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        connector = _make_connector(max_retries=0)

        # Create a real Pydantic ValidationError
        try:
            Keywords(sachgebiete="not_a_list", schlagworte="not_a_list")  # type: ignore[arg-type]
        except PydanticValidationError as ve:
            validation_exc = ve

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[validation_exc],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(
            LLMValidationError, match="could not produce valid Keywords"
        ):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_last_attempt_provider_error_raises_provider_error(self) -> None:
        """When the last attempt is a provider error, it determines the classification
        regardless of earlier validation errors."""
        from pydantic import ValidationError as PydanticValidationError

        connector = _make_connector(max_retries=0)

        try:
            Keywords(sachgebiete="bad", schlagworte="bad")  # type: ignore[arg-type]
        except PydanticValidationError as ve:
            validation_exc = ve

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[
                    validation_exc,
                    litellm.RateLimitError("rate limited", "model", "provider"),
                ],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMRateLimitError):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_last_attempt_validation_error_raises_validation_error(self) -> None:
        """When the last attempt is a validation error, it determines the classification
        regardless of earlier provider errors."""
        from pydantic import ValidationError as PydanticValidationError

        connector = _make_connector(max_retries=0)

        try:
            Keywords(sachgebiete="bad", schlagworte="bad")  # type: ignore[arg-type]
        except PydanticValidationError as ve:
            validation_exc = ve

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[
                    litellm.RateLimitError("rate limited", "model", "provider"),
                    validation_exc,
                ],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(
            LLMValidationError, match="could not produce valid Keywords"
        ):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_no_failed_attempts_falls_back_to_validation_error(self) -> None:
        """When failed_attempts is empty/None, fall back to LLMValidationError."""
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(failed_exceptions=None)
        )
        connector._instructor_client = mock_client

        with pytest.raises(
            LLMValidationError, match="could not produce valid Keywords"
        ):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_cause_chain_fallback_detects_provider_error(self) -> None:
        """When failed_attempts has no provider errors but __cause__ does,
        the __cause__ chain is used."""
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[],
                cause=litellm.AuthenticationError("bad key", "model", "provider"),
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMAuthenticationError):
            await connector.extract(prompt="test", response_model=Keywords)

    @pytest.mark.asyncio
    async def test_cause_chain_preserved(self) -> None:
        """The original InstructorRetryException is preserved as __cause__."""
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        retry_exc = _make_instructor_retry(
            failed_exceptions=[litellm.RateLimitError("limited", "model", "provider")],
        )
        mock_client.chat.completions.create = AsyncMock(side_effect=retry_exc)
        connector._instructor_client = mock_client

        with pytest.raises(LLMRateLimitError) as exc_info:
            await connector.extract(prompt="test", response_model=Keywords)

        assert exc_info.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_retryable_provider_error_gets_network_retry(self) -> None:
        """A retryable provider error (rate limit) extracted from
        InstructorRetryException should trigger network-level retries."""
        connector = _make_connector(max_retries=1)
        expected = Keywords(sachgebiete=["Justiz"], schlagworte=["Urteil"])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _make_instructor_retry(
                    failed_exceptions=[
                        litellm.RateLimitError("limited", "model", "provider")
                    ],
                ),
                expected,
            ]
        )
        connector._instructor_client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await connector.extract(prompt="test", response_model=Keywords)

        assert result == expected
        assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_unknown_exception_in_retry_raises_generic_provider_error(
        self,
    ) -> None:
        """An unrecognised (non-litellm) exception inside
        InstructorRetryException falls through to generic LLMProviderError."""
        connector = _make_connector(max_retries=0)
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_make_instructor_retry(
                failed_exceptions=[RuntimeError("something unexpected")],
            )
        )
        connector._instructor_client = mock_client

        with pytest.raises(LLMProviderError, match="provider request failed"):
            await connector.extract(prompt="test", response_model=Keywords)


# ---------------------------------------------------------------------------
# summarize_dokument() and summarize_gesetzentwurf()
# ---------------------------------------------------------------------------


# Valid (>= min length, non-echo) summaries reused by the mock-return tests.
_SUMMARY_DOKUMENT = (
    "Eine allgemeine Zusammenfassung des Dokuments mit den wesentlichen "
    "Aussagen und ihrem Kontext."
)
_SUMMARY_GESETZENTWURF = (
    "Der Gesetzentwurf regelt die Verwaltung der Bezirke neu und legt ihre "
    "künftigen Aufgaben sowie deren Finanzierung fest."
)


class TestSummarizeDokument:
    """Tests for LLMConnector.summarize_dokument()."""

    @pytest.mark.asyncio
    async def test_returns_zusammenfassung_string(self) -> None:
        connector = _make_connector()
        with patch.object(
            connector,
            "extract",
            new=AsyncMock(
                return_value=ZusammenfassungResult(zusammenfassung=_SUMMARY_DOKUMENT)
            ),
        ):
            result = await connector.summarize_dokument(
                titel="Stellungnahme", text="Inhalt des Dokuments."
            )
        assert result == _SUMMARY_DOKUMENT

    @pytest.mark.asyncio
    async def test_empty_titel_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError):
            await connector.summarize_dokument(titel="   ", text="Inhalt.")

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError):
            await connector.summarize_dokument(titel="Titel", text="   ")

    @pytest.mark.asyncio
    async def test_prompt_contains_titel_and_text(self) -> None:
        connector = _make_connector()
        captured: list[str] = []

        async def capture_extract(
            prompt: str, response_model: type, **kwargs: object
        ) -> ZusammenfassungResult:
            captured.append(prompt)
            return ZusammenfassungResult(zusammenfassung=_SUMMARY_DOKUMENT)

        with patch.object(connector, "extract", new=capture_extract):
            await connector.summarize_dokument(
                titel="Mein Titel", text="Mein Textinhalt."
            )

        assert len(captured) == 1
        assert "Mein Titel" in captured[0]
        assert "Mein Textinhalt." in captured[0]


class TestSummarizeGesetzentwurf:
    """Tests for LLMConnector.summarize_gesetzentwurf()."""

    @pytest.mark.asyncio
    async def test_returns_zusammenfassung_string(self) -> None:
        connector = _make_connector()
        with patch.object(
            connector,
            "extract",
            new=AsyncMock(
                return_value=ZusammenfassungResult(
                    zusammenfassung=_SUMMARY_GESETZENTWURF
                )
            ),
        ):
            result = await connector.summarize_gesetzentwurf(
                titel="Gesetzentwurf", text="Normtext."
            )
        assert result == _SUMMARY_GESETZENTWURF

    @pytest.mark.asyncio
    async def test_empty_titel_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError):
            await connector.summarize_gesetzentwurf(titel="   ", text="Normtext.")

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError):
            await connector.summarize_gesetzentwurf(titel="Titel", text="   ")

    @pytest.mark.asyncio
    async def test_prompt_contains_titel_and_text(self) -> None:
        connector = _make_connector()
        captured: list[str] = []

        async def capture_extract(
            prompt: str, response_model: type, **kwargs: object
        ) -> ZusammenfassungResult:
            captured.append(prompt)
            return ZusammenfassungResult(zusammenfassung=_SUMMARY_DOKUMENT)

        with patch.object(connector, "extract", new=capture_extract):
            await connector.summarize_gesetzentwurf(
                titel="Entwurf Schulgesetz", text="Gesetzestext."
            )

        assert len(captured) == 1
        assert "Entwurf Schulgesetz" in captured[0]
        assert "Gesetzestext." in captured[0]

    @pytest.mark.asyncio
    async def test_uses_different_prompt_than_dokument(self) -> None:
        """Gesetzentwurf method uses a more specific prompt than summarize_dokument."""
        connector = _make_connector()
        gesetzentwurf_prompts: list[str] = []
        dokument_prompts: list[str] = []

        async def capture_gesetzentwurf(
            prompt: str, response_model: type, **kwargs: object
        ) -> ZusammenfassungResult:
            gesetzentwurf_prompts.append(prompt)
            return ZusammenfassungResult(zusammenfassung=_SUMMARY_DOKUMENT)

        async def capture_dokument(
            prompt: str, response_model: type, **kwargs: object
        ) -> ZusammenfassungResult:
            dokument_prompts.append(prompt)
            return ZusammenfassungResult(zusammenfassung=_SUMMARY_DOKUMENT)

        with patch.object(connector, "extract", new=capture_gesetzentwurf):
            await connector.summarize_gesetzentwurf(titel="T", text="Text.")
        with patch.object(connector, "extract", new=capture_dokument):
            await connector.summarize_dokument(titel="T", text="Text.")

        assert gesetzentwurf_prompts[0] != dokument_prompts[0]
        # Gesetzentwurf prompt must contain law-specific structure.
        assert "Geänderte Vorschriften" in gesetzentwurf_prompts[0]
        assert "Inkrafttreten" in gesetzentwurf_prompts[0]
        # Generic prompt must not contain Gesetzentwurf-specific structure.
        assert "Geänderte Vorschriften" not in dokument_prompts[0]
        assert "Inkrafttreten" not in dokument_prompts[0]
