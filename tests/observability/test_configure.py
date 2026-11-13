"""Tests for ``pazufa_corelib.observability._configure``.

The global tracer and meter providers can only be set once per process, so
these tests patch ``get_*_provider`` / ``set_*_provider`` and inspect the
providers ``configure()`` hands over instead of installing them. litellm's
OpenTelemetry class is replaced by a stub: the real one would set the global
provider itself on construction.
"""

import logging
import uuid
from collections.abc import Iterator
from typing import Any

import litellm
import litellm.integrations.opentelemetry as litellm_otel
import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from pazufa_corelib.observability import _configure
from pazufa_corelib.observability._attributes import (
    DEPLOYMENT_ENVIRONMENT_NAME,
    PAZUFA_PARLIAMENT,
    PAZUFA_SCRAPER_ID,
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
)
from pazufa_corelib.observability._configure import (
    CAPTURE_CONTENT_ENV,
    LITELLM_OTEL_V2_ENV,
    LITELLM_REQUEST_SPAN_ENV,
    OTLP_METRICS_ENDPOINT_ENV_VARS,
    OTLP_TRACES_ENDPOINT_ENV_VARS,
    SERVICE_INSTANCE_ID_NAMESPACE,
    build_resource,
    configure,
)
from pazufa_corelib.observability._log_exporter import LoggingSpanExporter

_ENV_VARS = (
    *OTLP_TRACES_ENDPOINT_ENV_VARS,
    *OTLP_METRICS_ENDPOINT_ENV_VARS,
    "OTEL_RESOURCE_ATTRIBUTES",
    "OTEL_SERVICE_NAME",
    CAPTURE_CONTENT_ENV,
    LITELLM_REQUEST_SPAN_ENV,
    LITELLM_OTEL_V2_ENV,
)


class FakeOpenTelemetry:
    def __init__(self, config: Any) -> None:
        self.config = config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # delenv also restores whatever configure() sets via os.environ.setdefault.
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[TracerProvider]]:
    """Collect providers configure() would install; start with none installed."""
    providers: list[TracerProvider] = []

    def current() -> Any:
        return providers[-1] if providers else trace.NoOpTracerProvider()

    monkeypatch.setattr(trace, "get_tracer_provider", current)
    monkeypatch.setattr(trace, "set_tracer_provider", providers.append)
    yield providers
    for provider in providers:
        provider.shutdown()


@pytest.fixture(autouse=True)
def installed_meters(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[MeterProvider]]:
    """Same as ``installed`` for meter providers; autouse so no test sets one."""
    providers: list[MeterProvider] = []

    def current() -> Any:
        return providers[-1] if providers else metrics.NoOpMeterProvider()

    monkeypatch.setattr(metrics, "get_meter_provider", current)
    monkeypatch.setattr(metrics, "set_meter_provider", providers.append)
    yield providers
    for provider in providers:
        provider.shutdown()


@pytest.fixture
def litellm_callbacks(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    callbacks: list[Any] = []
    monkeypatch.setattr(litellm, "callbacks", callbacks)
    monkeypatch.setattr(litellm_otel, "OpenTelemetry", FakeOpenTelemetry)
    return callbacks


def _processors(provider: TracerProvider) -> list[Any]:
    return list(provider._active_span_processor._span_processors)


def test_installs_provider_with_log_exporter_only(
    installed: list[TracerProvider],
) -> None:
    configure("scraper-test")

    [provider] = installed
    [processor] = _processors(provider)
    assert isinstance(processor, SimpleSpanProcessor)
    assert isinstance(processor.span_exporter, LoggingSpanExporter)
    assert provider.resource.attributes["service.name"] == "scraper-test"


def test_service_name_falls_back_to_env(
    installed: list[TracerProvider], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OTEL_SERVICE_NAME", "from-env")
    configure()
    assert installed[0].resource.attributes["service.name"] == "from-env"


def test_argument_wins_over_env_service_name(
    installed: list[TracerProvider], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OTEL_SERVICE_NAME", "from-env")
    configure("from-argument")
    assert installed[0].resource.attributes["service.name"] == "from-argument"


@pytest.mark.parametrize("env_var", OTLP_TRACES_ENDPOINT_ENV_VARS)
def test_otlp_exporter_added_when_endpoint_set(
    installed: list[TracerProvider], monkeypatch: pytest.MonkeyPatch, env_var: str
) -> None:
    monkeypatch.setenv(env_var, "http://localhost:4318")
    configure()

    log_processor, otlp_processor = _processors(installed[0])
    assert isinstance(log_processor, SimpleSpanProcessor)
    assert isinstance(otlp_processor, BatchSpanProcessor)


def test_keeps_existing_sdk_provider(
    installed: list[TracerProvider], caplog: pytest.LogCaptureFixture
) -> None:
    configure()
    with caplog.at_level(logging.INFO, logger=_configure.LOGGER.name):
        configure()

    assert len(installed) == 1
    assert "already configured" in caplog.text


def test_litellm_not_instrumented_by_default(
    installed: list[TracerProvider], litellm_callbacks: list[Any]
) -> None:
    configure()
    assert litellm_callbacks == []


def test_litellm_callback_registered_once_without_content(
    installed: list[TracerProvider], litellm_callbacks: list[Any]
) -> None:
    configure(instrument_litellm=True)
    configure(instrument_litellm=True)

    [callback] = litellm_callbacks
    assert isinstance(callback, FakeOpenTelemetry)
    assert callback.config.capture_message_content == "NO_CONTENT"
    assert _configure.os.environ[LITELLM_REQUEST_SPAN_ENV] == "true"


def test_litellm_content_capture_can_be_opted_in(
    installed: list[TracerProvider],
    litellm_callbacks: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CAPTURE_CONTENT_ENV, "SPAN_ONLY")
    configure(instrument_litellm=True)
    assert litellm_callbacks[0].config.capture_message_content == "SPAN_ONLY"


def test_litellm_request_span_env_is_not_overridden(
    installed: list[TracerProvider],
    litellm_callbacks: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LITELLM_REQUEST_SPAN_ENV, "false")
    configure(instrument_litellm=True)
    assert _configure.os.environ[LITELLM_REQUEST_SPAN_ENV] == "false"


def test_litellm_v2_flag_logs_warning(
    installed: list[TracerProvider],
    litellm_callbacks: list[Any],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv(LITELLM_OTEL_V2_ENV, "true")
    with caplog.at_level(logging.WARNING, logger=_configure.LOGGER.name):
        configure(instrument_litellm=True)

    assert LITELLM_OTEL_V2_ENV in caplog.text
    assert len(litellm_callbacks) == 1


# --- Resource -------------------------------------------------------------------


def test_resource_attributes_on_both_providers(
    installed: list[TracerProvider],
    installed_meters: list[MeterProvider],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://localhost:4318")
    configure(
        "pazufa-scraper",
        resource_attributes={
            DEPLOYMENT_ENVIRONMENT_NAME: "staging",
            PAZUFA_PARLIAMENT: "BW",
        },
    )

    [tracer_provider] = installed
    [meter_provider] = installed_meters
    for resource in (tracer_provider.resource, meter_provider._sdk_config.resource):
        assert resource.attributes[SERVICE_NAME] == "pazufa-scraper"
        assert resource.attributes[DEPLOYMENT_ENVIRONMENT_NAME] == "staging"
        assert resource.attributes[PAZUFA_PARLIAMENT] == "BW"


def test_instance_id_derived_from_scraper_id() -> None:
    first = build_resource(resource_attributes={PAZUFA_SCRAPER_ID: "uuid-bw"})
    second = build_resource(resource_attributes={PAZUFA_SCRAPER_ID: "uuid-bw"})

    expected = str(uuid.uuid5(SERVICE_INSTANCE_ID_NAMESPACE, "uuid-bw"))
    assert first.attributes[SERVICE_INSTANCE_ID] == expected
    assert second.attributes[SERVICE_INSTANCE_ID] == expected


def test_explicit_instance_id_is_kept() -> None:
    resource = build_resource(
        resource_attributes={PAZUFA_SCRAPER_ID: "uuid-bw", SERVICE_INSTANCE_ID: "own"}
    )
    assert resource.attributes[SERVICE_INSTANCE_ID] == "own"


def test_instance_id_is_random_per_process_without_scraper_id() -> None:
    # The SDK fills in a random UUID (once per process), so every scraper run
    # would report as a new instance.
    value = build_resource("svc").attributes[SERVICE_INSTANCE_ID]
    assert uuid.UUID(str(value)).version == 4


def test_explicit_attributes_win_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        "pazufa.parliament=BT,deployment.environment.name=prod",
    )
    resource = build_resource(resource_attributes={PAZUFA_PARLIAMENT: "BW"})

    assert resource.attributes[PAZUFA_PARLIAMENT] == "BW"
    assert resource.attributes[DEPLOYMENT_ENVIRONMENT_NAME] == "prod"


def test_service_name_argument_wins_over_resource_attributes() -> None:
    resource = build_resource("arg", {SERVICE_NAME: "attr"})
    assert resource.attributes[SERVICE_NAME] == "arg"


# --- Metrics --------------------------------------------------------------------


def test_no_meter_provider_without_metrics_endpoint(
    installed_meters: list[MeterProvider], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4318")
    configure()
    assert installed_meters == []


@pytest.mark.parametrize("env_var", OTLP_METRICS_ENDPOINT_ENV_VARS)
def test_meter_provider_with_otlp_reader_when_endpoint_set(
    installed_meters: list[MeterProvider],
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
) -> None:
    monkeypatch.setenv(env_var, "http://localhost:4318")
    configure()

    [provider] = installed_meters
    [reader] = provider._metric_readers
    assert isinstance(reader, PeriodicExportingMetricReader)


def test_keeps_existing_meter_provider(
    installed_meters: list[MeterProvider],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://localhost:4318")
    configure()
    with caplog.at_level(logging.INFO, logger=_configure.LOGGER.name):
        configure()

    assert len(installed_meters) == 1
    assert "metrics already configured" in caplog.text
