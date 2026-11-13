"""Tests for ``pazufa_corelib.observability._tracing``."""

from collections.abc import Iterator

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode

from pazufa_corelib.observability import _tracing
from pazufa_corelib.observability._attributes import (
    EVENT_LLM_RETRY,
    GEN_AI_REQUEST_MODEL,
    LLM_ATTEMPT,
    TRACER_NAME,
)
from pazufa_corelib.observability._tracing import is_available, record_event, span


@pytest.fixture
def exporter(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemorySpanExporter]:
    # Swap the module tracer for one from a local provider: the global provider
    # can only be set once per process.
    memory = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory))
    monkeypatch.setattr(_tracing, "_TRACER", provider.get_tracer(TRACER_NAME))
    yield memory


def test_is_available_with_api_installed() -> None:
    assert is_available() is True


def test_span_records_name_and_attributes(exporter: InMemorySpanExporter) -> None:
    with span("op", {GEN_AI_REQUEST_MODEL: "gpt-x"}) as current:
        assert current is not None
        current.set_attribute(LLM_ATTEMPT, 1)

    [finished] = exporter.get_finished_spans()
    assert finished.name == "op"
    assert finished.instrumentation_scope is not None
    assert finished.instrumentation_scope.name == TRACER_NAME
    assert dict(finished.attributes or {}) == {
        GEN_AI_REQUEST_MODEL: "gpt-x",
        LLM_ATTEMPT: 1,
    }


def test_span_records_exception_and_reraises(exporter: InMemorySpanExporter) -> None:
    with pytest.raises(ValueError, match="boom"):
        with span("op"):
            raise ValueError("boom")

    [finished] = exporter.get_finished_spans()
    assert finished.status.status_code is StatusCode.ERROR
    assert [event.name for event in finished.events] == ["exception"]


def test_nested_spans_share_trace(exporter: InMemorySpanExporter) -> None:
    with span("outer"):
        with span("inner"):
            pass

    inner, outer = exporter.get_finished_spans()
    assert inner.parent is not None
    assert inner.parent.span_id == outer.context.span_id
    assert inner.context.trace_id == outer.context.trace_id


def test_record_event_lands_on_current_span(exporter: InMemorySpanExporter) -> None:
    with span("op"):
        record_event(EVENT_LLM_RETRY, {LLM_ATTEMPT: 2})

    [finished] = exporter.get_finished_spans()
    [event] = finished.events
    assert event.name == EVENT_LLM_RETRY
    assert dict(event.attributes or {}) == {LLM_ATTEMPT: 2}


def test_record_event_outside_span_is_noop(exporter: InMemorySpanExporter) -> None:
    record_event(EVENT_LLM_RETRY)
    assert exporter.get_finished_spans() == ()


def test_without_opentelemetry_everything_is_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_tracing, "_otel_trace", None)
    monkeypatch.setattr(_tracing, "_TRACER", None)

    assert is_available() is False
    with span("op", {GEN_AI_REQUEST_MODEL: "gpt-x"}) as current:
        record_event(EVENT_LLM_RETRY)
        assert current is None


def test_without_opentelemetry_exceptions_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_tracing, "_TRACER", None)
    with pytest.raises(KeyError):
        with span("op"):
            raise KeyError("x")
