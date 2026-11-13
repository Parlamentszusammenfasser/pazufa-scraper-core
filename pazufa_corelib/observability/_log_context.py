"""Logging filter that adds trace context to log records.

Meant for Scrapy's ``LOG_FORMAT`` (or any stdlib logging setup): it only adds
attributes to records and never configures handlers or formats.

Two ways to attach it:

* ``TraceContextFilter`` on a handler you own.
* ``install_trace_context()`` for Scrapy: wraps the log record factory, so every
  record carries the attributes from the start, including the startup lines
  logged before a handler filter could be attached.

Only depends on ``opentelemetry-api``; without it both IDs are ``"-"``.
"""

import logging
from collections.abc import Callable
from typing import Any

NO_TRACE: str = "-"

try:
    from opentelemetry import trace as _otel_trace
except ImportError:
    _otel_trace = None  # type: ignore[assignment]


def current_trace_ids() -> tuple[str, str]:
    """Return the hex trace and span ID of the active span.

    Returns:
        ``(trace_id, span_id)`` as 32 and 16 hex characters, or
        ``("-", "-")`` when no span is active or OpenTelemetry is missing.
    """
    if _otel_trace is None:
        return NO_TRACE, NO_TRACE
    context = _otel_trace.get_current_span().get_span_context()
    if not context.is_valid:
        return NO_TRACE, NO_TRACE
    return (
        _otel_trace.format_trace_id(context.trace_id),
        _otel_trace.format_span_id(context.span_id),
    )


def _inject(record: logging.LogRecord) -> None:
    record.trace_id, record.span_id = current_trace_ids()


class TraceContextFilter(logging.Filter):
    """Add ``trace_id`` and ``span_id`` attributes to every log record.

    Outside an active span both are set to ``"-"``, so a format string such as
    ``"%(asctime)s [%(trace_id).8s] %(message)s"`` never fails. Attach it to a
    handler, not a logger: logger filters do not see records propagated from
    child loggers.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach the current trace context to ``record``.

        Args:
            record: The log record being processed.

        Returns:
            Always ``True``; the filter never drops records.
        """
        _inject(record)
        return True


class _TraceContextRecordFactory:
    """Log record factory that wraps another one and adds trace context."""

    def __init__(self, wrapped: Callable[..., logging.LogRecord]) -> None:
        self.wrapped = wrapped

    def __call__(self, *args: Any, **kwargs: Any) -> logging.LogRecord:
        record = self.wrapped(*args, **kwargs)
        _inject(record)
        return record


def install_trace_context() -> None:
    """Add ``trace_id`` and ``span_id`` to every log record in this process.

    Wraps the current log record factory, keeping any factory installed before.
    Calling it again is a no-op. Call it early, e.g. at the top of a Scrapy
    ``settings.py``, before ``LOG_FORMAT`` references the attributes.

    Note:
        Afterwards ``logger.info(..., extra={"trace_id": ...})`` raises
        ``KeyError``, because stdlib logging refuses ``extra`` keys that already
        exist on the record.
    """
    current = logging.getLogRecordFactory()
    if isinstance(current, _TraceContextRecordFactory):
        return
    logging.setLogRecordFactory(_TraceContextRecordFactory(current))
