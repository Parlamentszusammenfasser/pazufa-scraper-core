"""Application-side OpenTelemetry setup for scrapers.

Needs the ``otel-otlp`` extra. SDK and exporter modules are imported inside
``configure()`` so that importing this module stays cheap.
"""

import logging
import os

LOGGER = logging.getLogger(__name__)

OTLP_ENDPOINT_ENV_VARS: tuple[str, ...] = (
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
)
CAPTURE_CONTENT_ENV = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
LITELLM_REQUEST_SPAN_ENV = "USE_OTEL_LITELLM_REQUEST_SPAN"
LITELLM_OTEL_V2_ENV = "LITELLM_OTEL_V2"


def configure(
    service_name: str | None = None,
    *,
    instrument_litellm: bool = False,
) -> None:
    """Set up tracing with readable span log lines and optional OTLP export.

    Installs a global ``TracerProvider`` that writes one log line per corelib
    span (``LoggingSpanExporter``) and, only if ``OTEL_EXPORTER_OTLP_ENDPOINT``
    or ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`` is set, exports all spans via
    OTLP/HTTP. If an SDK provider is already set up (for example under
    ``opentelemetry-instrument``), it is kept unchanged. Safe to call twice.

    Args:
        service_name: ``service.name`` resource attribute. Defaults to
            ``OTEL_SERVICE_NAME`` or the SDK default.
        instrument_litellm: Also trace litellm calls as child spans of the
            corelib spans, through the same provider. Prompt and response
            content is not recorded unless
            ``OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`` says so.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

    from ._log_exporter import LoggingSpanExporter

    if isinstance(trace.get_tracer_provider(), TracerProvider):
        LOGGER.info("OpenTelemetry SDK already configured; keeping existing provider")
    else:
        attributes = {"service.name": service_name} if service_name else {}
        provider = TracerProvider(resource=Resource.create(attributes))
        # Simple (synchronous) processor: the line lands in order with other logs.
        provider.add_span_processor(SimpleSpanProcessor(LoggingSpanExporter()))
        if any(os.environ.get(name) for name in OTLP_ENDPOINT_ENV_VARS):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            # Batch processor: network export never blocks the scraper.
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)

    if instrument_litellm:
        _instrument_litellm()


def _instrument_litellm() -> None:
    """Register litellm's (V1) OpenTelemetry callback once.

    Registering an instance instead of the string ``"otel"`` pins litellm's V1
    integration, which reuses the global provider set up by ``configure()``.
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
