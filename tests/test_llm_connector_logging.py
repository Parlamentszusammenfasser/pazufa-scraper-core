"""Structured ``extra`` fields of the LLMConnector logs.

The fields are what an OTLP log handler exports as attributes, so besides their
values these tests check that every field holds a valid attribute type.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest
from pydantic import BaseModel

from pazufa_corelib.llm.llm_connector import (
    LLMAuthenticationError,
    LLMConnector,
    LLMTemporaryProviderError,
)
from pazufa_corelib.llm.models import SectionExtractionResult
from pazufa_corelib.observability._attributes import (
    ERROR_TYPE,
    EXCEPTION_MESSAGE,
    GEN_AI_REQUEST_MODEL,
    LLM_API_KEY_SET,
    LLM_ATTEMPT,
    LLM_CHUNK_COUNT,
    LLM_CHUNK_INDEX,
    LLM_CHUNK_LINE_END,
    LLM_CHUNK_LINE_START,
    LLM_CONFIG_DEFAULT,
    LLM_CONFIG_PARAMETER,
    LLM_CONFIG_VALUE,
    LLM_LINES_EXTRACTED,
    LLM_LINES_TOTAL,
    LLM_MAPPED_ERROR_TYPE,
    LLM_MAX_RETRIES,
    LLM_RATE_LIMITER_ENABLED,
    LLM_RATE_LIMITER_MAX_CALLS,
    LLM_RATE_LIMITER_WINDOW,
    LLM_RETRY_DELAY,
    LLM_TIMEOUT,
)

LOGGER_NAME = "pazufa_corelib.llm.llm_connector"
MODEL = "openai/gpt-4o-mini"
_ATTRIBUTE_TYPES = (str, int, float, bool)
_FIELD_PREFIXES = ("pazufa.", "gen_ai.", "error.", "exception.")


class Keywords(BaseModel):
    schlagworte: list[str]


@pytest.fixture
def logs(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        yield caplog
    _assert_valid_fields(caplog.records)


def _connector(**kwargs: object) -> LLMConnector:
    defaults: dict[str, object] = {
        "model": MODEL,
        "rate_limit_max_calls": None,
        "max_retries": 1,
    }
    defaults.update(kwargs)
    return LLMConnector(**defaults)  # type: ignore[arg-type]


def _fields(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: value
        for key, value in vars(record).items()
        if key.startswith(_FIELD_PREFIXES)
    }


def _record(caplog: pytest.LogCaptureFixture, message_start: str) -> logging.LogRecord:
    matches = [r for r in caplog.records if r.getMessage().startswith(message_start)]
    assert len(matches) == 1, [r.getMessage() for r in caplog.records]
    return matches[0]


def _assert_valid_fields(records: list[logging.LogRecord]) -> None:
    """Every record has fields, and each one is a valid log attribute value."""
    for record in records:
        fields = _fields(record)
        assert fields, f"no extra fields on {record.getMessage()!r}"
        for key, value in fields.items():
            assert isinstance(value, _ATTRIBUTE_TYPES), (key, value)


# --- Construction -----------------------------------------------------------------


def test_init_fields(logs: pytest.LogCaptureFixture) -> None:
    _connector(timeout_seconds=30, max_retries=2)

    assert _fields(_record(logs, "Initialized LLMConnector")) == {
        GEN_AI_REQUEST_MODEL: MODEL,
        LLM_API_KEY_SET: False,
        LLM_RATE_LIMITER_ENABLED: False,
        LLM_TIMEOUT: 30.0,
        LLM_MAX_RETRIES: 2,
    }


def test_invalid_config_names_parameter_value_and_default(
    logs: pytest.LogCaptureFixture,
) -> None:
    _connector(max_retries="drei")

    assert _fields(_record(logs, "max_retries must be")) == {
        LLM_CONFIG_PARAMETER: "max_retries",
        LLM_CONFIG_VALUE: "'drei'",
        LLM_CONFIG_DEFAULT: 3,
    }


def test_invalid_temperature_has_no_default(logs: pytest.LogCaptureFixture) -> None:
    _connector(temperature=float("nan"))

    fields = _fields(_record(logs, "temperature must be"))
    assert fields == {LLM_CONFIG_PARAMETER: "temperature", LLM_CONFIG_VALUE: "nan"}


def test_api_key_value_is_never_logged(logs: pytest.LogCaptureFixture) -> None:
    _connector(api_key=987654321)

    record = _record(logs, "API key is not a string")
    assert _fields(record) == {LLM_CONFIG_PARAMETER: "api_key", ERROR_TYPE: "int"}
    assert "987654321" not in repr(vars(record))


def test_rate_limiter_failure_fields(logs: pytest.LogCaptureFixture) -> None:
    _connector(rate_limit_max_calls=0, rate_limit_window_seconds="eine Minute")

    fields = _fields(_record(logs, "Failed to initialize local rate limiter"))
    assert fields[LLM_RATE_LIMITER_ENABLED] is False
    assert fields[LLM_RATE_LIMITER_MAX_CALLS] == 0
    assert fields[ERROR_TYPE] == "ValueError"
    assert EXCEPTION_MESSAGE in fields
    # Not a number, so not a valid attribute value: left out instead.
    assert LLM_RATE_LIMITER_WINDOW not in fields


# --- extract() ---------------------------------------------------------------------


def _client(side_effect: object) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=side_effect)
    return client


def _timeout() -> Exception:
    return litellm.exceptions.Timeout(
        message="timeout", model="test", llm_provider="openai"
    )


@pytest.mark.asyncio
async def test_retry_and_final_failure_fields(logs: pytest.LogCaptureFixture) -> None:
    connector = _connector(max_retries=1)
    connector._instructor_client = _client([_timeout(), _timeout()])

    with patch(
        "pazufa_corelib.llm.llm_connector.asyncio.sleep", new_callable=AsyncMock
    ):
        with pytest.raises(LLMTemporaryProviderError):
            await connector.extract(prompt="test", response_model=Keywords)

    retry = _fields(_record(logs, "Retrying extraction"))
    assert retry[GEN_AI_REQUEST_MODEL] == MODEL
    assert retry[LLM_ATTEMPT] == 2
    assert retry[LLM_MAX_RETRIES] == 1
    assert retry[ERROR_TYPE] == "LLMTemporaryProviderError"
    assert isinstance(retry[LLM_RETRY_DELAY], float)

    failed = _record(logs, "Extraction failed without retry")
    assert failed.levelno == logging.ERROR
    assert _fields(failed)[LLM_ATTEMPT] == 2
    assert _fields(failed)[ERROR_TYPE] == "LLMTemporaryProviderError"


@pytest.mark.asyncio
async def test_provider_failure_has_raw_and_mapped_error(
    logs: pytest.LogCaptureFixture,
) -> None:
    connector = _connector(max_retries=0)
    connector._instructor_client = _client(
        litellm.AuthenticationError(
            message="Invalid API key",
            llm_provider="openai",
            model="gpt-4o-mini",
            response=MagicMock(status_code=401),
        )
    )

    with pytest.raises(LLMAuthenticationError):
        await connector.extract(prompt="test", response_model=Keywords)

    fields = _fields(_record(logs, "Provider call failed"))
    assert fields[ERROR_TYPE] == "AuthenticationError"
    assert fields[LLM_MAPPED_ERROR_TYPE] == "LLMAuthenticationError"
    assert "Invalid API key" in str(fields[EXCEPTION_MESSAGE])


@pytest.mark.asyncio
async def test_successful_extract_logs_valid_fields(
    logs: pytest.LogCaptureFixture,
) -> None:
    connector = _connector(rate_limit_max_calls=5, rate_limit_max_tokens=50_000)
    connector._instructor_client = _client([Keywords(schlagworte=["Haushalt"])])

    await connector.extract(prompt="test", response_model=Keywords)

    # The logs fixture checks every record, incl. rate limiter and token estimate.
    assert _fields(_record(logs, "Structured extraction successful"))[LLM_ATTEMPT] == 1


# --- extract_relevant_section() ---------------------------------------------------


@pytest.mark.asyncio
async def test_chunk_fields(logs: pytest.LogCaptureFixture) -> None:
    connector = _connector()
    connector.extract = AsyncMock(  # type: ignore[method-assign]
        return_value=SectionExtractionResult(is_relevant=False)
    )

    with patch(
        "pazufa_corelib.llm.llm_connector.litellm.token_counter", return_value=1
    ):
        result = await connector.extract_relevant_section(
            "Zeile eins\nZeile zwei\nZeile drei", vorgang_titel="Haushaltsgesetz"
        )

    assert result is None
    split = _fields(_record(logs, "Split document"))
    assert split[LLM_CHUNK_COUNT] == 1
    assert split[LLM_LINES_TOTAL] == 3
    chunk = _fields(_record(logs, "Processing chunk"))
    assert chunk[LLM_CHUNK_INDEX] == 1
    assert (chunk[LLM_CHUNK_LINE_START], chunk[LLM_CHUNK_LINE_END]) == (1, 3)
    none_found = _fields(_record(logs, "No relevant content"))
    assert none_found == {LLM_LINES_EXTRACTED: 0, LLM_LINES_TOTAL: 3}
