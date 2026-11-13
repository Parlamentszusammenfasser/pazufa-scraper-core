"""Tests for ``pazufa_corelib.observability._log_exporter``."""

import logging

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from opentelemetry.trace import format_trace_id

from pazufa_corelib.observability._attributes import (
    ERROR_TYPE,
    EVENT_RATE_LIMIT_WAIT,
    EVENT_RETRY,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    PAZUFA_ATTEMPT,
    PAZUFA_WAIT_SECONDS,
    SPAN_LLM_EXTRACT,
    TELEMETRY_LOGGER_NAME,
    TRACER_NAME,
)
from pazufa_corelib.observability._log_exporter import LoggingSpanExporter


def _provider(exporter: LoggingSpanExporter) -> TracerProvider:
    # Local provider per test: the global one can only be set once per process.
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider


@pytest.fixture
def exporter() -> LoggingSpanExporter:
    return LoggingSpanExporter()


def test_successful_span_is_one_info_line(
    exporter: LoggingSpanExporter, caplog: pytest.LogCaptureFixture
) -> None:
    tracer = _provider(exporter).get_tracer(TRACER_NAME)
    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        with tracer.start_as_current_span(SPAN_LLM_EXTRACT) as span:
            span.set_attributes(
                {
                    GEN_AI_REQUEST_MODEL: "gpt-x",
                    GEN_AI_USAGE_INPUT_TOKENS: 1200,
                    GEN_AI_USAGE_OUTPUT_TOKENS: 34,
                    PAZUFA_ATTEMPT: 2,
                    "pazufa.scraper.not_shown": "hidden",
                }
            )
            span.add_event(EVENT_RETRY, {ERROR_TYPE: "LLMRateLimitError"})
            span.add_event(EVENT_RATE_LIMIT_WAIT, {PAZUFA_WAIT_SECONDS: 0.25})
            span.add_event(EVENT_RATE_LIMIT_WAIT, {PAZUFA_WAIT_SECONDS: 0.15})
            trace_id = format_trace_id(span.get_span_context().trace_id)

    [record] = caplog.records
    assert record.levelno == logging.INFO
    line = record.getMessage()
    assert line.startswith(f"{SPAN_LLM_EXTRACT} ok ")
    assert (
        "model=gpt-x input_tokens=1200 output_tokens=34 attempt=2 "
        "retries=1 waited=0.40s" in line
    )
    assert line.endswith(f"trace={trace_id}")
    assert "hidden" not in line


def test_failed_span_is_warning_with_exception_type(
    exporter: LoggingSpanExporter, caplog: pytest.LogCaptureFixture
) -> None:
    tracer = _provider(exporter).get_tracer(TRACER_NAME)
    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        with pytest.raises(TimeoutError):
            with tracer.start_as_current_span(SPAN_LLM_EXTRACT):
                raise TimeoutError("provider timed out")

    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert f"{SPAN_LLM_EXTRACT} error " in record.getMessage()
    assert "error=TimeoutError" in record.getMessage()


def test_error_type_attribute_wins_over_exception_event(
    exporter: LoggingSpanExporter, caplog: pytest.LogCaptureFixture
) -> None:
    tracer = _provider(exporter).get_tracer(TRACER_NAME)
    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        with pytest.raises(RuntimeError):
            with tracer.start_as_current_span(SPAN_LLM_EXTRACT) as span:
                span.set_attribute(ERROR_TYPE, "LLMQuotaExceededError")
                raise RuntimeError("wrapped")

    assert "error=LLMQuotaExceededError" in caplog.records[0].getMessage()


def test_spans_from_other_scopes_are_skipped(
    exporter: LoggingSpanExporter, caplog: pytest.LogCaptureFixture
) -> None:
    provider = _provider(exporter)
    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        with provider.get_tracer("litellm").start_as_current_span("litellm_request"):
            pass
    assert caplog.records == []


def test_scope_none_logs_every_span(caplog: pytest.LogCaptureFixture) -> None:
    provider = _provider(LoggingSpanExporter(scope_name=None))
    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        with provider.get_tracer("litellm").start_as_current_span("litellm_request"):
            pass
    assert caplog.records[0].getMessage().startswith("litellm_request ok ")


def test_custom_logger_is_used(caplog: pytest.LogCaptureFixture) -> None:
    custom = logging.getLogger("scraper.telemetry")
    provider = _provider(LoggingSpanExporter(custom))
    with caplog.at_level(logging.INFO, logger=custom.name):
        with provider.get_tracer(TRACER_NAME).start_as_current_span("op"):
            pass
    assert [r.name for r in caplog.records] == ["scraper.telemetry"]


def test_unformattable_span_is_skipped_without_failing_export(
    exporter: LoggingSpanExporter,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(span: ReadableSpan) -> str:
        raise ValueError("cannot format")

    finished: list[ReadableSpan] = []

    class Collect(SimpleSpanProcessor):
        def on_end(self, span: ReadableSpan) -> None:
            finished.append(span)

    provider = TracerProvider()
    provider.add_span_processor(Collect(exporter))
    with provider.get_tracer(TRACER_NAME).start_as_current_span("op"):
        pass

    monkeypatch.setattr(LoggingSpanExporter, "format_span", staticmethod(broken))
    with caplog.at_level(logging.INFO, logger=TELEMETRY_LOGGER_NAME):
        assert exporter.export(finished) is SpanExportResult.SUCCESS
    assert caplog.records == []


def test_list_attribute_values_are_joined() -> None:
    provider = TracerProvider()
    span = provider.get_tracer(TRACER_NAME).start_span(
        "op", attributes={GEN_AI_REQUEST_MODEL: ["a", "b"]}
    )
    span.end()
    assert isinstance(span, ReadableSpan)
    assert "model=a,b" in LoggingSpanExporter.format_span(span)
