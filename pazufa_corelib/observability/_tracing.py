"""Span helper that degrades to a no-op without OpenTelemetry.

Only depends on ``opentelemetry-api`` (extra ``otel``). Without an SDK
configured by the application, the API itself is a no-op, so spans here are
cheap enough for library code.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING

from ._attributes import TRACER_NAME

if TYPE_CHECKING:
    from opentelemetry.trace import Span

AttrValue = str | int | float | bool

try:
    from opentelemetry import trace as _otel_trace
except ImportError:
    _otel_trace = None  # type: ignore[assignment]

# Safe at import time: before the application sets a provider this is a proxy
# tracer that forwards to the real one once it is set.
_TRACER = _otel_trace.get_tracer(TRACER_NAME) if _otel_trace is not None else None


def is_available() -> bool:
    """Return whether the OpenTelemetry API is installed.

    Returns:
        ``True`` if ``opentelemetry-api`` can be imported, else ``False``.
    """
    return _otel_trace is not None


@contextmanager
def span(
    name: str, attributes: Mapping[str, AttrValue] | None = None
) -> Iterator["Span | None"]:
    """Start a span named ``name`` as the current span.

    An exception leaving the block is recorded on the span and sets its status
    to ERROR, then propagates unchanged. Without OpenTelemetry installed this
    yields ``None`` and does nothing, so callers guard span calls with
    ``if s is not None:``.

    Args:
        name: Span name, see ``_attributes`` for the defined names.
        attributes: Initial span attributes. A mapping rather than keyword
            arguments, because attribute names contain dots.

    Yields:
        The active span, or ``None`` if OpenTelemetry is not installed.
    """
    if _TRACER is None:
        yield None
        return
    with _TRACER.start_as_current_span(name, attributes=attributes) as current:
        yield current


def record_event(name: str, attributes: Mapping[str, AttrValue] | None = None) -> None:
    """Add an event to the currently active span.

    Needs no span handle, so code deep inside a call (e.g. the rate limiter)
    can annotate the surrounding span. Does nothing without OpenTelemetry or
    outside a span.

    Args:
        name: Event name, see ``_attributes`` for the defined names.
        attributes: Optional event attributes.
    """
    if _otel_trace is not None:
        _otel_trace.get_current_span().add_event(name, attributes=attributes)
