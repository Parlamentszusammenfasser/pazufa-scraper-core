"""Spans and metrics recorded by the LLMConnector.

The module tracer and metric instruments are swapped for ones on local
providers with in-memory exporters: global providers can only be set once per
process. Provider calls are mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    HistogramDataPoint,
    InMemoryMetricReader,
    NumberDataPoint,
)
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode
from pydantic import BaseModel

from pazufa_corelib.llm.llm_connector import (
    LLMAuthenticationError,
    LLMConnector,
    RateLimiter,
)
from pazufa_corelib.llm.models import SectionExtractionResult, ZusammenfassungResult
from pazufa_corelib.observability import _metrics, _tracing
from pazufa_corelib.observability._attributes import (
    ERROR_TYPE,
    EVENT_LLM_RATE_LIMITED,
    EVENT_LLM_RETRY,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_TOKEN_TYPE,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    LLM_ATTEMPT,
    LLM_OPERATION,
    LLM_RATE_LIMITER_DELAY,
    LLM_RESPONSE_MODEL,
    LLM_RETRY_DELAY,
    METRIC_GEN_AI_OPERATION_DURATION,
    METRIC_GEN_AI_TOKEN_USAGE,
    METRIC_LLM_OPERATION_DURATION,
    METRIC_LLM_RATE_LIMITER_WAIT_DURATION,
    METRIC_LLM_REASONING_TOKEN_USAGE,
    METRIC_LLM_RETRIES,
    SPAN_LLM_EXTRACT,
    SPAN_LLM_EXTRACT_RELEVANT_SECTION,
    SPAN_LLM_SUMMARIZE,
    TRACER_NAME,
)

MODEL = "openai/gpt-4o-mini"


class Keywords(BaseModel):
    schlagworte: list[str]


# --- Fixtures -----------------------------------------------------------------------


@pytest.fixture
def spans(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    monkeypatch.setattr(_tracing, "_TRACER", provider.get_tracer(TRACER_NAME))
    return memory


@pytest.fixture
def metrics(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemoryMetricReader]:
    memory = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[memory])
    instruments = _metrics._create_instruments(provider.get_meter(TRACER_NAME))
    monkeypatch.setattr(_metrics, "_INSTRUMENTS", instruments)
    yield memory
    provider.shutdown()


# --- Helpers ------------------------------------------------------------------------


def _connector(**kwargs: object) -> LLMConnector:
    defaults: dict[str, object] = {
        "model": MODEL,
        "rate_limit_max_calls": None,
        "max_retries": 1,
    }
    defaults.update(kwargs)
    return LLMConnector(**defaults)  # type: ignore[arg-type]


def _with_usage(
    result: BaseModel, prompt: int, completion: int, reasoning: int = 0
) -> Any:
    usage = SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning),
    )
    object.__setattr__(result, "_raw_response", SimpleNamespace(usage=usage))
    return result


def _client(side_effect: object) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=side_effect)
    return client


def _timeout() -> Exception:
    return litellm.exceptions.Timeout(
        message="timeout", model="test", llm_provider="openai"
    )


def _span(exporter: InMemorySpanExporter, name: str) -> ReadableSpan:
    matches = [s for s in exporter.get_finished_spans() if s.name == name]
    assert len(matches) == 1, [s.name for s in exporter.get_finished_spans()]
    return matches[0]


def _points(reader: InMemoryMetricReader, name: str) -> dict[frozenset, Any]:
    """Map each attribute set to its value (sum, or (count, sum) for histograms)."""
    data = reader.get_metrics_data()
    result: dict[frozenset, Any] = {}
    if data is None:
        return result
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name != name:
                    continue
                for point in metric.data.data_points:
                    key = frozenset((point.attributes or {}).items())
                    if isinstance(point, HistogramDataPoint):
                        result[key] = (point.count, point.sum)
                    else:
                        assert isinstance(point, NumberDataPoint)
                        result[key] = point.value
    return result


def _by(points: dict[frozenset, Any], key: str) -> dict[Any, Any]:
    """Re-key metric points by the value of one attribute."""
    return {dict(attrs).get(key): value for attrs, value in points.items()}


# --- extract() ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_extract_span_and_metrics(
    spans: InMemorySpanExporter, metrics: InMemoryMetricReader
) -> None:
    connector = _connector()
    result = _with_usage(Keywords(schlagworte=["Haushalt"]), 1200, 34, reasoning=10)
    connector._instructor_client = _client([result])

    await connector.extract(prompt="test", response_model=Keywords)

    span = _span(spans, SPAN_LLM_EXTRACT)
    assert span.status.status_code is not StatusCode.ERROR
    attributes = dict(span.attributes or {})
    assert attributes[LLM_OPERATION] == "extract"
    assert attributes[GEN_AI_REQUEST_MODEL] == MODEL
    assert attributes[GEN_AI_PROVIDER_NAME] == "openai"
    assert attributes[LLM_RESPONSE_MODEL] == "Keywords"
    assert attributes[LLM_ATTEMPT] == 1
    assert attributes[GEN_AI_USAGE_INPUT_TOKENS] == 1200
    assert attributes[GEN_AI_USAGE_OUTPUT_TOKENS] == 34

    tokens = _by(_points(metrics, METRIC_GEN_AI_TOKEN_USAGE), GEN_AI_TOKEN_TYPE)
    assert tokens == {"input": (1, 1200), "output": (1, 34)}
    [reasoning] = _points(metrics, METRIC_LLM_REASONING_TOKEN_USAGE).values()
    assert reasoning == (1, 10)
    [call] = _points(metrics, METRIC_GEN_AI_OPERATION_DURATION)
    assert ERROR_TYPE not in dict(call)
    assert dict(call)[GEN_AI_PROVIDER_NAME] == "openai"
    operations = _by(_points(metrics, METRIC_LLM_OPERATION_DURATION), LLM_OPERATION)
    assert operations["extract"][0] == 1


@pytest.mark.asyncio
async def test_retry_records_event_counter_and_failed_call(
    spans: InMemorySpanExporter, metrics: InMemoryMetricReader
) -> None:
    connector = _connector(max_retries=1)
    connector._instructor_client = _client(
        [_timeout(), _with_usage(Keywords(schlagworte=[]), 100, 5)]
    )

    with patch(
        "pazufa_corelib.llm.llm_connector.asyncio.sleep", new_callable=AsyncMock
    ):
        await connector.extract(prompt="test", response_model=Keywords)

    span = _span(spans, SPAN_LLM_EXTRACT)
    assert dict(span.attributes or {})[LLM_ATTEMPT] == 2
    [retry] = [e for e in span.events if e.name == EVENT_LLM_RETRY]
    assert dict(retry.attributes or {})[ERROR_TYPE] == "LLMTemporaryProviderError"
    assert dict(retry.attributes or {})[LLM_ATTEMPT] == 2
    assert isinstance(dict(retry.attributes or {})[LLM_RETRY_DELAY], float)

    [retries] = _points(metrics, METRIC_LLM_RETRIES).values()
    assert retries == 1
    calls = _by(_points(metrics, METRIC_GEN_AI_OPERATION_DURATION), ERROR_TYPE)
    assert calls["Timeout"][0] == 1
    assert calls[None][0] == 1


@pytest.mark.asyncio
async def test_failed_extract_marks_span_and_operation(
    spans: InMemorySpanExporter, metrics: InMemoryMetricReader
) -> None:
    connector = _connector(max_retries=2)
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

    span = _span(spans, SPAN_LLM_EXTRACT)
    assert span.status.status_code is StatusCode.ERROR
    assert dict(span.attributes or {})[ERROR_TYPE] == "LLMAuthenticationError"
    operations = _by(_points(metrics, METRIC_LLM_OPERATION_DURATION), ERROR_TYPE)
    assert operations["LLMAuthenticationError"][0] == 1
    # No usage reported: no token points, and no retry for auth errors.
    assert _points(metrics, METRIC_GEN_AI_TOKEN_USAGE) == {}
    assert _points(metrics, METRIC_LLM_RETRIES) == {}


@pytest.mark.asyncio
async def test_invalid_input_creates_no_span(spans: InMemorySpanExporter) -> None:
    connector = _connector()

    with pytest.raises(ValueError, match="prompt must not be empty"):
        await connector.extract(prompt="  ", response_model=Keywords)

    assert spans.get_finished_spans() == ()


# --- Composite operations -----------------------------------------------------------


@pytest.mark.asyncio
async def test_summarize_span_is_parent_of_extract(
    spans: InMemorySpanExporter, metrics: InMemoryMetricReader
) -> None:
    connector = _connector()
    summary = ZusammenfassungResult.model_construct(zusammenfassung="Kurz.")
    connector._instructor_client = _client([summary])

    await connector.summarize_dokument("Titel", "Text")

    parent = _span(spans, SPAN_LLM_SUMMARIZE)
    child = _span(spans, SPAN_LLM_EXTRACT)
    assert child.parent is not None
    assert child.parent.span_id == parent.context.span_id
    assert dict(parent.attributes or {})[LLM_OPERATION] == "summarize"
    operations = _by(_points(metrics, METRIC_LLM_OPERATION_DURATION), LLM_OPERATION)
    assert set(operations) == {"summarize", "extract"}


@pytest.mark.asyncio
async def test_relevant_section_span_wraps_chunk_extracts(
    spans: InMemorySpanExporter,
) -> None:
    connector = _connector()
    connector._instructor_client = _client(
        [SectionExtractionResult(is_relevant=False)] * 2
    )

    with patch(
        "pazufa_corelib.llm.llm_connector.litellm.token_counter", return_value=1
    ):
        await connector.extract_relevant_section(
            "a\nb\nc\nd", vorgang_titel="Haushalt", chunk_size=2, chunk_overlap=0
        )

    parent = _span(spans, SPAN_LLM_EXTRACT_RELEVANT_SECTION)
    children = [s for s in spans.get_finished_spans() if s.name == SPAN_LLM_EXTRACT]
    assert len(children) == 2
    assert all(
        c.parent and c.parent.span_id == parent.context.span_id for c in children
    )


# --- RateLimiter --------------------------------------------------------------------


def test_rate_limiter_records_wait_and_event(
    spans: InMemorySpanExporter, metrics: InMemoryMetricReader
) -> None:
    limiter = RateLimiter(max_calls=1, per_seconds=0.05)

    async def two_calls() -> None:
        with _tracing.span("outer"):
            await limiter.acquire_slot()
            await limiter.acquire_slot()

    asyncio.run(two_calls())

    [event] = [
        e for e in _span(spans, "outer").events if e.name == EVENT_LLM_RATE_LIMITED
    ]
    assert 0 < float(dict(event.attributes or {})[LLM_RATE_LIMITER_DELAY]) <= 0.05
    # One point per acquired slot, including the one that did not wait.
    [(count, _)] = _points(metrics, METRIC_LLM_RATE_LIMITER_WAIT_DURATION).values()
    assert count == 2
