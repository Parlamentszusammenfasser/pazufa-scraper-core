"""Application-side OpenTelemetry setup for scrapers.

Needs the ``otel-otlp`` extra. SDK and exporter modules are imported inside
``configure()`` so that importing this module stays cheap.
"""

import logging
import os
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING

from ._attributes import PAZUFA_SCRAPER_ID, SERVICE_INSTANCE_ID, SERVICE_NAME
from ._tracing import AttrValue

if TYPE_CHECKING:
    from opentelemetry.sdk.resources import Resource

LOGGER = logging.getLogger(__name__)

OTLP_TRACES_ENDPOINT_ENV_VARS: tuple[str, ...] = (
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
)
OTLP_METRICS_ENDPOINT_ENV_VARS: tuple[str, ...] = (
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
)
CAPTURE_CONTENT_ENV = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
LITELLM_REQUEST_SPAN_ENV = "USE_OTEL_LITELLM_REQUEST_SPAN"
LITELLM_OTEL_V2_ENV = "LITELLM_OTEL_V2"

# Namespace the semantic conventions prescribe for deriving a stable
# service.instance.id (UUIDv5) from an inherent unique ID.
SERVICE_INSTANCE_ID_NAMESPACE = uuid.UUID("4d63009a-8d0f-11ee-aad7-4c796ed8e320")


def configure(
    service_name: str | None = None,
    *,
    resource_attributes: Mapping[str, AttrValue] | None = None,
    instrument_litellm: bool = False,
) -> None:
    """Set up tracing and metrics with readable span logs and optional OTLP export.

    Traces: installs a global ``TracerProvider`` that writes one log line per
    corelib span (``LoggingSpanExporter``) and, if ``OTEL_EXPORTER_OTLP_ENDPOINT``
    or ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`` is set, exports all spans via
    OTLP/HTTP.

    Metrics: installs a global ``MeterProvider`` that exports via OTLP/HTTP, only
    if ``OTEL_EXPORTER_OTLP_ENDPOINT`` or ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT``
    is set. Without an endpoint metrics stay no-ops. The final values are
    exported when the process exits normally.

    Both providers share one resource. A provider that is already an SDK
    provider (for example under ``opentelemetry-instrument``) is kept
    unchanged. Safe to call twice.

    Args:
        service_name: ``service.name``. Defaults to ``OTEL_SERVICE_NAME`` or the
            SDK default.
        resource_attributes: Further resource attributes, e.g.
            ``deployment.environment.name``, ``pazufa.scraper.id``,
            ``pazufa.parliament``, ``service.version`` (see ``_attributes``).
            They override ``OTEL_RESOURCE_ATTRIBUTES``. If ``pazufa.scraper.id``
            is set and ``service.instance.id`` is not, the latter is derived from
            it, so every run of a scraper reports as the same instance.
        instrument_litellm: Also trace litellm calls as child spans of the
            corelib spans, through the same provider. Prompt and response
            content is not recorded unless
            ``OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`` says so.
    """
    resource = build_resource(service_name, resource_attributes)
    _configure_tracing(resource)
    _configure_metrics(resource)
    if instrument_litellm:
        _instrument_litellm()


def build_resource(
    service_name: str | None = None,
    resource_attributes: Mapping[str, AttrValue] | None = None,
) -> "Resource":
    """Build the resource shared by the tracer and meter provider.

    Args:
        service_name: ``service.name``; overrides one in ``resource_attributes``.
        resource_attributes: Further resource attributes.

    Returns:
        The SDK resource, merged with ``OTEL_RESOURCE_ATTRIBUTES`` and
        ``OTEL_SERVICE_NAME`` (explicit values win).
    """
    from opentelemetry.sdk.resources import Resource

    attributes: dict[str, AttrValue] = dict(resource_attributes or {})
    if service_name:
        attributes[SERVICE_NAME] = service_name
    scraper_id = attributes.get(PAZUFA_SCRAPER_ID)
    if scraper_id is not None and SERVICE_INSTANCE_ID not in attributes:
        attributes[SERVICE_INSTANCE_ID] = str(
            uuid.uuid5(SERVICE_INSTANCE_ID_NAMESPACE, str(scraper_id))
        )
    return Resource.create(attributes)


def _configure_tracing(resource: "Resource") -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

    from ._log_exporter import LoggingSpanExporter

    if isinstance(trace.get_tracer_provider(), TracerProvider):
        LOGGER.info("OpenTelemetry tracing already configured; keeping provider")
        return
    provider = TracerProvider(resource=resource)
    # Simple (synchronous) processor: the line lands in order with other logs.
    provider.add_span_processor(SimpleSpanProcessor(LoggingSpanExporter()))
    if _is_set(OTLP_TRACES_ENDPOINT_ENV_VARS):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        # Batch processor: network export never blocks the scraper.
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)


def _configure_metrics(resource: "Resource") -> None:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider

    if isinstance(metrics.get_meter_provider(), MeterProvider):
        LOGGER.info("OpenTelemetry metrics already configured; keeping provider")
        return
    if not _is_set(OTLP_METRICS_ENDPOINT_ENV_VARS):
        LOGGER.debug("No OTLP metrics endpoint set; metrics are not exported")
        return
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    # Exports every OTEL_METRIC_EXPORT_INTERVAL ms (default 60 s) and once more
    # when the provider shuts down at process exit.
    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[reader])
    )


def _is_set(env_vars: tuple[str, ...]) -> bool:
    return any(os.environ.get(name) for name in env_vars)


def _instrument_litellm() -> None:
    """Register litellm's (V1) OpenTelemetry callback once.

    Registering an instance instead of the string ``"otel"`` pins litellm's V1
    integration, which reuses the global provider set up by ``configure()``.
    litellm's own metrics stay off (``enable_metrics=False``); the corelib
    records the GenAI metrics itself.
    """
    import litellm
    from litellm.integrations.opentelemetry import (
        OpenTelemetry,
        OpenTelemetryConfig,
    )

    if any(isinstance(callback, OpenTelemetry) for callback in litellm.callbacks):
        return
    if os.environ.get(LITELLM_OTEL_V2_ENV):
        LOGGER.warning(
            "%s is set, but pazufa_corelib registers litellm's V1 OpenTelemetry "
            "integration, which reuses the corelib's tracer provider",
            LITELLM_OTEL_V2_ENV,
        )
    # Without it, litellm writes onto the corelib span, which has already ended
    # when litellm's async success callback runs.
    os.environ.setdefault(LITELLM_REQUEST_SPAN_ENV, "true")
    # litellm records prompts and responses unless told otherwise.
    capture = os.environ.get(CAPTURE_CONTENT_ENV, "NO_CONTENT")
    litellm.callbacks.append(
        OpenTelemetry(config=OpenTelemetryConfig(capture_message_content=capture))
    )
