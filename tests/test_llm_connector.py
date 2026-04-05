from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest
from pydantic import BaseModel, Field

from collector_core.llm.llm_connector import (
    TOKEN_ESTIMATE_OUTPUT_BUFFER,
    LLMAuthenticationError,
    LLMConnector,
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
    with patch("instructor.from_litellm", return_value=MagicMock()):
        return LLMConnector(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# extract() — input validation
# ---------------------------------------------------------------------------


class TestExtractInputValidation:
    """Verify that extract() rejects invalid inputs before calling the model."""

    def test_empty_prompt_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="prompt must not be empty"):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt="   ", response_model=Keywords)
            )

    def test_non_string_prompt_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="prompt must be a string"):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt=42, response_model=Keywords)  # type: ignore[arg-type]
            )

    def test_non_basemodel_response_model_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="response_model must be a Pydantic BaseModel"
        ):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt="test", response_model=dict)  # type: ignore[arg-type,type-var]
            )

    def test_string_response_model_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="response_model must be a Pydantic BaseModel"
        ):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt="test", response_model="Keywords")  # type: ignore[arg-type]
            )

    def test_negative_validation_retries_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="validation_retries must be a non-negative integer"
        ):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(
                    prompt="test", response_model=Keywords, validation_retries=-1
                )
            )

    def test_bool_validation_retries_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(
            ValueError, match="validation_retries must be a non-negative integer"
        ):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(
                    prompt="test",
                    response_model=Keywords,
                    validation_retries=True,  # type: ignore[arg-type]
                )
            )

    def test_non_string_system_prompt_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="system_prompt must be a string or None"):
            asyncio.get_event_loop().run_until_complete(
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
            "collector_core.llm.llm_connector.asyncio.sleep", new_callable=AsyncMock
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
            "collector_core.llm.llm_connector.asyncio.sleep", new_callable=AsyncMock
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
            "collector_core.llm.llm_connector.litellm.token_counter",
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
            "collector_core.llm.llm_connector.litellm.token_counter",
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
            "collector_core.llm.llm_connector.litellm.token_counter",
            side_effect=lambda model, text: len(text.split()) if text else 0,
        ):
            result = connector._estimate_request_tokens(messages)

        # "" (empty fallback) = 0 words, "Hello" = 1 word
        assert result == 1 + TOKEN_ESTIMATE_OUTPUT_BUFFER
