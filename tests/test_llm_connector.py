from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest
from pydantic import BaseModel, Field

from collector_core.llm_connector import (
    RETRY_BASE_DELAY_SECONDS,
    RETRY_JITTER_MAX_SECONDS,
    RETRY_JITTER_MIN_SECONDS,
    LLMAuthenticationError,
    LLMConnector,
    LLMConnectorError,
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
        with pytest.raises(ValueError, match="response_model must be a Pydantic BaseModel"):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt="test", response_model=dict)  # type: ignore[arg-type]
            )

    def test_string_response_model_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="response_model must be a Pydantic BaseModel"):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt="test", response_model="Keywords")  # type: ignore[arg-type]
            )

    def test_negative_validation_retries_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="validation_retries must be a non-negative integer"):
            asyncio.get_event_loop().run_until_complete(
                connector.extract(prompt="test", response_model=Keywords, validation_retries=-1)
            )

    def test_bool_validation_retries_raises(self) -> None:
        connector = _make_connector()
        with pytest.raises(ValueError, match="validation_retries must be a non-negative integer"):
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
                    prompt="test", response_model=Keywords, system_prompt=123  # type: ignore[arg-type]
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
        assert call_kwargs["messages"][0] == {"role": "system", "content": "Be precise."}
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

        await connector.extract(prompt="test", response_model=Keywords, validation_retries=0)

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

        with pytest.raises(LLMValidationError, match="could not produce valid Keywords"):
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
                litellm.exceptions.Timeout(message="timeout", model="test", llm_provider="openai"),
                expected,
            ]
        )
        connector._instructor_client = mock_client

        with patch("collector_core.llm_connector.asyncio.sleep", new_callable=AsyncMock):
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

        with patch("collector_core.llm_connector.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMTemporaryProviderError):
                await connector.extract(prompt="test", response_model=Keywords)

        assert mock_client.chat.completions.create.call_count == 2


# ---------------------------------------------------------------------------
# extract() — lazy Instructor client init
# ---------------------------------------------------------------------------


class TestExtractLazyInit:
    """Verify the Instructor client is lazily initialized."""

    def test_instructor_client_none_after_init(self) -> None:
        connector = _make_connector()
        assert connector._instructor_client is None

    @pytest.mark.asyncio
    async def test_instructor_client_initialized_on_first_extract(self) -> None:
        connector = _make_connector()
        expected = Keywords(sachgebiete=[], schlagworte=[])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=expected)

        import instructor

        with patch.object(instructor, "from_litellm", return_value=mock_client) as mock_from:
            await connector.extract(prompt="test", response_model=Keywords)

            mock_from.assert_called_once_with(litellm.acompletion, mode=instructor.Mode.TOOLS)
            assert connector._instructor_client is mock_client

    @pytest.mark.asyncio
    async def test_instructor_client_reused_on_second_extract(self) -> None:
        connector = _make_connector()
        expected = Keywords(sachgebiete=[], schlagworte=[])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=expected)
        connector._instructor_client = mock_client

        import instructor

        with patch.object(instructor, "from_litellm") as mock_from:
            await connector.extract(prompt="test1", response_model=Keywords)
            await connector.extract(prompt="test2", response_model=Keywords)

            mock_from.assert_not_called()
