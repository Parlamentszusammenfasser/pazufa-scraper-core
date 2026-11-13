"""Optional OpenTelemetry support for pazufa_corelib.

Library code only uses the API-level helpers (``span``, ``record_event``, the
metric helpers), which work without OpenTelemetry installed. Application-side setup
(``configure``, ``LoggingSpanExporter``) needs the ``otel-otlp`` extra.

Every public name is imported lazily on first access. Importing this package,
or a submodule without OpenTelemetry imports such as ``_attributes``, loads no
``opentelemetry`` module: ``span`` and the metric helpers load the API, and
``configure`` / ``LoggingSpanExporter`` load the SDK.
"""

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._configure import configure
    from ._log_exporter import LoggingSpanExporter
    from ._metrics import (
        add_dropped,
        add_failed_entities,
        add_found_entities,
        add_llm_enrichments,
        add_llm_retry,
        add_near_ties,
        add_resolutions,
        add_skipped_entities,
        add_submitted_entities,
        record_gen_ai_operation_duration,
        record_llm_operation_duration,
        record_match_scores,
        record_rate_limiter_wait,
        record_run_duration,
        record_token_usage,
        set_run_last_success,
    )
    from ._tracing import is_available, record_event, set_span_attributes, span

_METRIC_HELPERS: tuple[str, ...] = (
    "add_dropped",
    "add_failed_entities",
    "add_found_entities",
    "add_llm_enrichments",
    "add_llm_retry",
    "add_near_ties",
    "add_resolutions",
    "add_skipped_entities",
    "add_submitted_entities",
    "record_gen_ai_operation_duration",
    "record_llm_operation_duration",
    "record_match_scores",
    "record_rate_limiter_wait",
    "record_run_duration",
    "record_token_usage",
    "set_run_last_success",
)

_LAZY_MODULES: dict[str, str] = {
    "configure": "._configure",
    "LoggingSpanExporter": "._log_exporter",
    "is_available": "._tracing",
    "record_event": "._tracing",
    "set_span_attributes": "._tracing",
    "span": "._tracing",
    **dict.fromkeys(_METRIC_HELPERS, "._metrics"),
}

_INSTALL_HINT = 'pip install "pazufa_corelib[otel-otlp]"'


def __getattr__(name: str) -> Any:
    """Import public symbols on first access.

    Args:
        name: Attribute name looked up on this package.

    Returns:
        The requested symbol.

    Raises:
        ImportError: If an SDK-backed symbol is requested without the
            ``otel-otlp`` extra installed.
        AttributeError: If ``name`` is not a public symbol of this package.
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
    "add_dropped",
    "add_failed_entities",
    "add_found_entities",
    "add_llm_enrichments",
    "add_llm_retry",
    "add_near_ties",
    "add_resolutions",
    "add_skipped_entities",
    "add_submitted_entities",
    "configure",
    "is_available",
    "record_event",
    "record_gen_ai_operation_duration",
    "record_llm_operation_duration",
    "record_match_scores",
    "record_rate_limiter_wait",
    "record_run_duration",
    "record_token_usage",
    "set_run_last_success",
    "set_span_attributes",
    "span",
]
