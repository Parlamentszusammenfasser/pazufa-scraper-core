"""Span exporter that writes one readable log line per finished span.

Needs the ``otel-otlp`` extra. Only imported lazily through
``pazufa_corelib.observability.__getattr__``, which is why the module-level SDK
import is allowed here.
"""

import logging
from collections.abc import Sequence
from typing import Final

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode, format_trace_id
from opentelemetry.util.types import AttributeValue

from ._attributes import (
    ERROR_TYPE,
    EVENT_LLM_RATE_LIMITED,
    EVENT_LLM_RETRY,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    LLM_ATTEMPT,
    LLM_RATE_LIMITER_DELAY,
    TELEMETRY_LOGGER_NAME,
    TRACER_NAME,
)

LOGGER = logging.getLogger(__name__)

# Span attributes shown in the log line, in this order, with their short labels.
# Everything else stays on the span for OTLP backends only.
_SHOWN_ATTRIBUTES: Final[tuple[tuple[str, str], ...]] = (
    (GEN_AI_REQUEST_MODEL, "model"),
    (GEN_AI_USAGE_INPUT_TOKENS, "input_tokens"),
    (GEN_AI_USAGE_OUTPUT_TOKENS, "output_tokens"),
    (LLM_ATTEMPT, "attempt"),
)
_EXCEPTION_EVENT: Final = "exception"
_EXCEPTION_TYPE: Final = "exception.type"


class LoggingSpanExporter(SpanExporter):
    """Export spans as human-readable lines through stdlib logging.

    Example lines::

        pazufa.llm.extract ok 1.82s model=gpt-x input_tokens=1200
            output_tokens=34 attempt=2 retries=1 waited=0.40s trace=4bf92f3a…
        pazufa.llm.extract error 3.10s model=gpt-x error=RateLimitError
            retries=2 trace=…

    Successful spans are logged at INFO, failed ones at WARNING, on the
    ``pazufa_corelib.telemetry`` logger. The full 32-character trace ID is
    logged, so it can be pasted into a tracing backend and still matches the
    8-character prefix from ``%(trace_id).8s`` in other log lines.

    Only spans from the ``scope_name`` instrumentation scope are logged, so
    litellm or HTTP spans going through the same provider do not flood the log.
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        *,
        scope_name: str | None = TRACER_NAME,
    ) -> None:
        self._logger = logger or logging.getLogger(TELEMETRY_LOGGER_NAME)
        self._scope_name = scope_name

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Log each finished span of the configured scope.

        Args:
            spans: Finished spans handed over by the span processor.

        Returns:
            ``SpanExportResult.SUCCESS``; a span that cannot be formatted is
            skipped instead of failing the export.
        """
        for span in spans:
            if not self._is_in_scope(span):
                continue
            try:
                line = self.format_span(span)
            except Exception:
                LOGGER.debug("Could not format span %r", span.name, exc_info=True)
                continue
            failed = span.status.status_code is StatusCode.ERROR
            self._logger.log(logging.WARNING if failed else logging.INFO, "%s", line)
        return SpanExportResult.SUCCESS

    def _is_in_scope(self, span: ReadableSpan) -> bool:
        if self._scope_name is None:
            return True
        scope = span.instrumentation_scope
        return scope is not None and scope.name == self._scope_name

    @staticmethod
    def format_span(span: ReadableSpan) -> str:
        """Render ``span`` as a single readable line.

        Args:
            span: A finished span.

        Returns:
            Name, status, duration, the attributes listed in
            ``_SHOWN_ATTRIBUTES``, the error type, retry count, total rate-limit
            wait and the trace ID, separated by spaces.
        """
        failed = span.status.status_code is StatusCode.ERROR
        parts = [span.name, "error" if failed else "ok"]

        if span.start_time is not None and span.end_time is not None:
            parts.append(f"{(span.end_time - span.start_time) / 1e9:.2f}s")

        attributes = span.attributes or {}
        for key, label in _SHOWN_ATTRIBUTES:
            if key in attributes:
                parts.append(f"{label}={_format_value(attributes[key])}")

        if failed:
            error_type = attributes.get(ERROR_TYPE) or _exception_type(span)
            if error_type:
                parts.append(f"error={_format_value(error_type)}")

        retries = sum(1 for event in span.events if event.name == EVENT_LLM_RETRY)
        if retries:
            parts.append(f"retries={retries}")

        waited = sum(
            float(wait)
            for event in span.events
            if event.name == EVENT_LLM_RATE_LIMITED
            and isinstance(
                wait := (event.attributes or {}).get(LLM_RATE_LIMITER_DELAY),
                int | float,
            )
        )
        if waited:
            parts.append(f"waited={waited:.2f}s")

        if span.context is not None:
            parts.append(f"trace={format_trace_id(span.context.trace_id)}")
        return " ".join(parts)


def _exception_type(span: ReadableSpan) -> AttributeValue | None:
    """Return the type of the last exception recorded on ``span``, if any."""
    for event in reversed(span.events):
        if event.name == _EXCEPTION_EVENT and event.attributes:
            return event.attributes.get(_EXCEPTION_TYPE)
    return None


def _format_value(value: AttributeValue) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list | tuple):
        return ",".join(str(item) for item in value)
    return str(value)
