"""Tests for ``pazufa_corelib.observability._log_context``."""

import logging
from collections.abc import Iterator

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import format_span_id, format_trace_id

from pazufa_corelib.observability import _log_context
from pazufa_corelib.observability._log_context import (
    NO_TRACE,
    TraceContextFilter,
    current_trace_ids,
    install_trace_context,
)

# A local provider: the global one can only be set once per process.
_TRACER = TracerProvider().get_tracer("test")


def _record() -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, __file__, 1, "msg", None, None)


@pytest.fixture
def restore_record_factory() -> Iterator[None]:
    original = logging.getLogRecordFactory()
    yield
    logging.setLogRecordFactory(original)


def test_ids_outside_span_are_placeholders() -> None:
    assert current_trace_ids() == (NO_TRACE, NO_TRACE)


def test_ids_inside_span_match_span_context() -> None:
    with _TRACER.start_as_current_span("op") as span:
        context = span.get_span_context()
        trace_id, span_id = current_trace_ids()
    assert trace_id == format_trace_id(context.trace_id)
    assert span_id == format_span_id(context.span_id)
    assert len(trace_id) == 32
    assert len(span_id) == 16


def test_ids_without_opentelemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_log_context, "_otel_trace", None)
    with _TRACER.start_as_current_span("op"):
        assert current_trace_ids() == (NO_TRACE, NO_TRACE)


def test_filter_sets_attributes_and_keeps_record() -> None:
    record = _record()
    assert TraceContextFilter().filter(record) is True
    assert record.trace_id == NO_TRACE
    assert record.span_id == NO_TRACE


def test_filter_makes_format_string_safe_outside_span() -> None:
    record = _record()
    TraceContextFilter().filter(record)
    formatter = logging.Formatter("[%(trace_id).8s] %(message)s")
    assert formatter.format(record) == "[-] msg"


@pytest.mark.usefixtures("restore_record_factory")
def test_install_adds_ids_to_logged_records(caplog: pytest.LogCaptureFixture) -> None:
    install_trace_context()
    logger = logging.getLogger("pazufa_corelib.test_log_context")
    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info("outside")
        with _TRACER.start_as_current_span("op") as span:
            logger.info("inside")
            expected = format_trace_id(span.get_span_context().trace_id)
    outside, inside = caplog.records
    assert outside.trace_id == NO_TRACE
    assert inside.trace_id == expected


@pytest.mark.usefixtures("restore_record_factory")
def test_install_is_idempotent_and_keeps_previous_factory() -> None:
    original = logging.getLogRecordFactory()
    install_trace_context()
    installed = logging.getLogRecordFactory()
    install_trace_context()
    assert logging.getLogRecordFactory() is installed
    assert installed.wrapped is original  # type: ignore[attr-defined]
