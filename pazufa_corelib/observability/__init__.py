"""Optional OpenTelemetry support for pazufa_corelib.

Library code only uses the API-level helpers (``span``, ``TraceContextFilter``,
the metric helpers), which work without OpenTelemetry installed. Application-side setup
(``configure``, ``LoggingSpanExporter``) needs the ``otel-otlp`` extra and is
imported lazily on first access, so a plain install never loads the SDK.
"""

import importlib
from typing import TYPE_CHECKING, Any

from ._log_context import (
    TraceContextFilter,
    current_trace_ids,
    install_trace_context,
)
from ._metrics import (
    add_failed_entities,
    add_found_entities,
    add_llm_enrichments,
    add_llm_retry,
    add_skipped_entities,
    add_submitted_entities,
    record_gen_ai_operation_duration,
    record_llm_operation_duration,
    record_rate_limiter_wait,
    record_run_duration,
    record_token_usage,
    set_run_last_success,
)
from ._tracing import is_available, record_event, span

if TYPE_CHECKING:
    from ._configure import configure
    from ._log_exporter import LoggingSpanExporter

_LAZY_MODULES: dict[str, str] = {
    "configure": "._configure",
    "LoggingSpanExporter": "._log_exporter",
}

_INSTALL_HINT = 'pip install "pazufa_corelib[otel-otlp]"'


def __getattr__(name: str) -> Any:
    """Import SDK-backed symbols on first access.

    Args:
        name: Attribute name looked up on this package.

    Returns:
        The requested symbol.

    Raises:
        ImportError: If the OpenTelemetry SDK extra is not installed.
        AttributeError: If ``name`` is not a lazily exported symbol.
    """
    if name in _LAZY_MODULES:
        try:
            module = importlib.import_module(_LAZY_MODULES[name], __name__)
        except ModuleNotFoundError as exc:
            if exc.name is not None and exc.name.startswith("opentelemetry"):
                raise ImportError(
                    f"{name} requires the OpenTelemetry SDK: {_INSTALL_HINT}"
                ) from exc
            raise
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LoggingSpanExporter",
    "TraceContextFilter",
    "add_failed_entities",
    "add_found_entities",
    "add_llm_enrichments",
    "add_llm_retry",
    "add_skipped_entities",
    "add_submitted_entities",
    "configure",
    "current_trace_ids",
    "install_trace_context",
    "is_available",
    "record_event",
    "record_gen_ai_operation_duration",
    "record_llm_operation_duration",
    "record_rate_limiter_wait",
    "record_run_duration",
    "record_token_usage",
    "set_run_last_success",
    "span",
]
