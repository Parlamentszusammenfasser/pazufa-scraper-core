"""Tests for ``pazufa_corelib.observability._metrics``.

Each test swaps the module instruments for ones on a local ``MeterProvider``
with an in-memory reader: the global provider can only be set once per process.
"""

from collections import Counter
from collections.abc import Iterator
from typing import Any

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    HistogramDataPoint,
    InMemoryMetricReader,
    NumberDataPoint,
)

from pazufa_corelib.observability import _metrics
from pazufa_corelib.observability._attributes import (
    ELECTION_PERIOD,
    ENRICHMENT_FIELD,
    ENRICHMENT_SOURCE,
    ENTITY_STATE,
    ENTITY_TYPE,
    ERROR_TYPE,
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_TOKEN_TYPE,
    HTTP_RESPONSE_STATUS_CODE,
    LLM_OPERATION,
    METRIC_GEN_AI_OPERATION_DURATION,
    METRIC_GEN_AI_TOKEN_USAGE,
    METRIC_LLM_OPERATION_DURATION,
    METRIC_LLM_RATE_LIMITER_WAIT_DURATION,
    METRIC_LLM_REASONING_TOKEN_USAGE,
    METRIC_LLM_RETRIES,
    METRIC_NORMALIZATION_DROPPED,
    METRIC_NORMALIZATION_MATCH_SCORE,
    METRIC_NORMALIZATION_NEAR_TIES,
    METRIC_NORMALIZATION_RESOLUTIONS,
    METRIC_SCRAPER_FAILED_ENTITIES,
    METRIC_SCRAPER_FOUND_ENTITIES,
    METRIC_SCRAPER_LLM_ENRICHMENTS,
    METRIC_SCRAPER_RUN_DURATION,
    METRIC_SCRAPER_RUN_LAST_SUCCESS,
    METRIC_SCRAPER_SKIPPED_ENTITIES,
    METRIC_SCRAPER_SUBMITTED_ENTITIES,
    NORMALIZATION_OUTCOME,
    NORMALIZATION_RESOLVER,
    SKIP_REASON,
    TRACER_NAME,
)


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemoryMetricReader]:
    memory = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[memory])
    instruments = _metrics._create_instruments(provider.get_meter(TRACER_NAME))
    monkeypatch.setattr(_metrics, "_INSTRUMENTS", instruments)
    monkeypatch.setattr(_metrics, "_last_success", None)
    yield memory
    provider.shutdown()


def _metric(reader: InMemoryMetricReader, name: str) -> Any | None:
    data = reader.get_metrics_data()
    if data is None:
        return None
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == name:
                    return metric
    return None


def _points(reader: InMemoryMetricReader, name: str) -> dict[frozenset, Any]:
    """Map each attribute set to its value (sum, or (count, sum) for histograms)."""
    metric = _metric(reader, name)
    assert metric is not None, f"{name} not recorded"
    result: dict[frozenset, Any] = {}
    for point in metric.data.data_points:
        key = frozenset((point.attributes or {}).items())
        if isinstance(point, HistogramDataPoint):
            result[key] = (point.count, point.sum)
        else:
            assert isinstance(point, NumberDataPoint)
            result[key] = point.value
    return result


def _attrs(**pairs: Any) -> frozenset:
    return frozenset(pairs.items())


# --- LLM ------------------------------------------------------------------------


def test_token_usage_per_token_type(reader: InMemoryMetricReader) -> None:
    _metrics.record_token_usage(
        model="gpt-x", input_tokens=1200, output_tokens=34, provider="openai"
    )

    base = {
        GEN_AI_OPERATION_NAME: "chat",
        GEN_AI_REQUEST_MODEL: "gpt-x",
        GEN_AI_PROVIDER_NAME: "openai",
    }
    assert _points(reader, METRIC_GEN_AI_TOKEN_USAGE) == {
        frozenset({**base, GEN_AI_TOKEN_TYPE: "input"}.items()): (1, 1200),
        frozenset({**base, GEN_AI_TOKEN_TYPE: "output"}.items()): (1, 34),
    }
    metric = _metric(reader, METRIC_GEN_AI_TOKEN_USAGE)
    assert metric.unit == "{token}"
    assert metric.data.data_points[0].explicit_bounds[:3] == (1.0, 4.0, 16.0)


def test_reasoning_tokens_on_own_metric(reader: InMemoryMetricReader) -> None:
    _metrics.record_token_usage(
        model="o-x", input_tokens=10, output_tokens=50, reasoning_tokens=40
    )

    assert _points(reader, METRIC_LLM_REASONING_TOKEN_USAGE) == {
        _attrs(**{GEN_AI_OPERATION_NAME: "chat", GEN_AI_REQUEST_MODEL: "o-x"}): (1, 40)
    }
    output = _points(reader, METRIC_GEN_AI_TOKEN_USAGE)
    assert sum(total for _, total in output.values()) == 60


def test_zero_token_counts_are_skipped(reader: InMemoryMetricReader) -> None:
    _metrics.record_token_usage(model="gpt-x", input_tokens=0, output_tokens=0)
    assert _metric(reader, METRIC_GEN_AI_TOKEN_USAGE) is None
    assert _metric(reader, METRIC_LLM_REASONING_TOKEN_USAGE) is None


def test_gen_ai_operation_duration_with_error(reader: InMemoryMetricReader) -> None:
    _metrics.record_gen_ai_operation_duration(1.5, model="gpt-x")
    _metrics.record_gen_ai_operation_duration(
        0.5, model="gpt-x", error_type="RateLimitError", provider="openai"
    )

    base = {GEN_AI_OPERATION_NAME: "chat", GEN_AI_REQUEST_MODEL: "gpt-x"}
    assert _points(reader, METRIC_GEN_AI_OPERATION_DURATION) == {
        frozenset(base.items()): (1, 1.5),
        frozenset(
            {
                **base,
                GEN_AI_PROVIDER_NAME: "openai",
                ERROR_TYPE: "RateLimitError",
            }.items()
        ): (1, 0.5),
    }
    metric = _metric(reader, METRIC_GEN_AI_OPERATION_DURATION)
    assert metric.unit == "s"
    assert metric.data.data_points[0].explicit_bounds[:3] == (0.01, 0.02, 0.04)


def test_llm_operation_duration_retry_and_wait(reader: InMemoryMetricReader) -> None:
    _metrics.record_llm_operation_duration(3.0, operation="extract", model="gpt-x")
    _metrics.add_llm_retry(operation="extract", model="gpt-x", error_type="Timeout")
    _metrics.add_llm_retry(operation="extract", model="gpt-x", error_type="Timeout")
    _metrics.record_rate_limiter_wait(0.25)

    llm = {LLM_OPERATION: "extract", GEN_AI_REQUEST_MODEL: "gpt-x"}
    assert _points(reader, METRIC_LLM_OPERATION_DURATION) == {
        frozenset(llm.items()): (1, 3.0)
    }
    assert _points(reader, METRIC_LLM_RETRIES) == {
        frozenset({**llm, ERROR_TYPE: "Timeout"}.items()): 2
    }
    assert _points(reader, METRIC_LLM_RATE_LIMITER_WAIT_DURATION) == {
        frozenset(): (1, 0.25)
    }


# --- Scraper ----------------------------------------------------------------------


def test_found_entities_including_zero(reader: InMemoryMetricReader) -> None:
    _metrics.add_found_entities(2, entity_type="procedure", state="new")
    _metrics.add_found_entities(0, entity_type="procedure", state="retried")

    assert _points(reader, METRIC_SCRAPER_FOUND_ENTITIES) == {
        _attrs(**{ENTITY_TYPE: "procedure", ENTITY_STATE: "new"}): 2,
        _attrs(**{ENTITY_TYPE: "procedure", ENTITY_STATE: "retried"}): 0,
    }


def test_submitted_entities_set_error_type_from_status(
    reader: InMemoryMetricReader,
) -> None:
    _metrics.add_submitted_entities(312, entity_type="procedure", status_code=201)
    _metrics.add_submitted_entities(2, entity_type="procedure", status_code=409)

    assert _points(reader, METRIC_SCRAPER_SUBMITTED_ENTITIES) == {
        _attrs(**{ENTITY_TYPE: "procedure", HTTP_RESPONSE_STATUS_CODE: 201}): 312,
        _attrs(
            **{
                ENTITY_TYPE: "procedure",
                HTTP_RESPONSE_STATUS_CODE: 409,
                ERROR_TYPE: "409",
            }
        ): 2,
    }


def test_skipped_and_failed_entities(reader: InMemoryMetricReader) -> None:
    _metrics.add_skipped_entities(21, entity_type="procedure", reason="out_of_scope")
    _metrics.add_failed_entities(3, entity_type="document", error_type="not_found")

    assert _points(reader, METRIC_SCRAPER_SKIPPED_ENTITIES) == {
        _attrs(**{ENTITY_TYPE: "procedure", SKIP_REASON: "out_of_scope"}): 21
    }
    assert _points(reader, METRIC_SCRAPER_FAILED_ENTITIES) == {
        _attrs(**{ENTITY_TYPE: "document", ERROR_TYPE: "not_found"}): 3
    }


def test_llm_enrichments(reader: InMemoryMetricReader) -> None:
    _metrics.add_llm_enrichments(
        7, entity_type="procedure", field="Kurztitel", source="cache"
    )
    _metrics.add_llm_enrichments(
        1,
        entity_type="procedure",
        field="Kurztitel",
        source="llm",
        error_type="LLMValidationError",
    )

    base = {ENTITY_TYPE: "procedure", ENRICHMENT_FIELD: "Kurztitel"}
    assert _points(reader, METRIC_SCRAPER_LLM_ENRICHMENTS) == {
        frozenset({**base, ENRICHMENT_SOURCE: "cache"}.items()): 7,
        frozenset(
            {**base, ENRICHMENT_SOURCE: "llm", ERROR_TYPE: "LLMValidationError"}.items()
        ): 1,
    }


def test_extra_attributes_cannot_override_schema(reader: InMemoryMetricReader) -> None:
    _metrics.add_found_entities(
        1,
        entity_type="procedure",
        state="new",
        attributes={ELECTION_PERIOD: "18", ENTITY_TYPE: "overridden"},
    )

    assert _points(reader, METRIC_SCRAPER_FOUND_ENTITIES) == {
        _attrs(
            **{ENTITY_TYPE: "procedure", ENTITY_STATE: "new", ELECTION_PERIOD: "18"}
        ): 1
    }


def test_run_duration(reader: InMemoryMetricReader) -> None:
    _metrics.record_run_duration(26.0)
    _metrics.record_run_duration(5.0, error_type="SourceUnavailable")

    assert _points(reader, METRIC_SCRAPER_RUN_DURATION) == {
        frozenset(): (1, 26.0),
        _attrs(**{ERROR_TYPE: "SourceUnavailable"}): (1, 5.0),
    }


def test_last_success_only_reported_after_success(
    reader: InMemoryMetricReader,
) -> None:
    assert _metric(reader, METRIC_SCRAPER_RUN_LAST_SUCCESS) is None

    _metrics.set_run_last_success(1_700_000_000.0)

    assert _points(reader, METRIC_SCRAPER_RUN_LAST_SUCCESS) == {
        frozenset(): 1_700_000_000.0
    }
    assert _metric(reader, METRIC_SCRAPER_RUN_LAST_SUCCESS).unit == "s"


def test_last_success_defaults_to_now(
    reader: InMemoryMetricReader, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_metrics.time, "time", lambda: 42.0)
    _metrics.set_run_last_success()
    assert _points(reader, METRIC_SCRAPER_RUN_LAST_SUCCESS) == {frozenset(): 42.0}


# --- Normalization ------------------------------------------------------------------


def _resolution(resolver: str, outcome: str) -> frozenset:
    return frozenset(
        {NORMALIZATION_RESOLVER: resolver, NORMALIZATION_OUTCOME: outcome}.items()
    )


def _by_resolver(resolver: str) -> frozenset:
    return frozenset({NORMALIZATION_RESOLVER: resolver}.items())


def test_resolutions_per_outcome_skip_zero(reader: InMemoryMetricReader) -> None:
    _metrics.add_resolutions(Counter(exact=3, fuzzy=1, unresolved=0), resolver="author")
    _metrics.add_resolutions({"exact": 2}, resolver="author")
    _metrics.add_resolutions({"unresolved": 4}, resolver="organization")

    assert _points(reader, METRIC_NORMALIZATION_RESOLUTIONS) == {
        _resolution("author", "exact"): 5,
        _resolution("author", "fuzzy"): 1,
        _resolution("organization", "unresolved"): 4,
    }


def test_match_scores_per_resolver(reader: InMemoryMetricReader) -> None:
    _metrics.record_match_scores([91.0, 95.5], resolver="author")
    _metrics.record_match_scores([], resolver="organization")

    assert _points(reader, METRIC_NORMALIZATION_MATCH_SCORE) == {
        _by_resolver("author"): (2, 186.5)
    }
    metric = _metric(reader, METRIC_NORMALIZATION_MATCH_SCORE)
    assert metric is not None
    assert metric.unit == "1"
    point = metric.data.data_points[0]
    assert tuple(point.explicit_bounds) == _metrics.MATCH_SCORE_BUCKETS


def test_near_ties_and_dropped_skip_zero(reader: InMemoryMetricReader) -> None:
    _metrics.add_near_ties(2, resolver="organization")
    _metrics.add_near_ties(0, resolver="author")
    _metrics.add_dropped(3, resolver="schlagwort")
    _metrics.add_dropped(0, resolver="author")

    assert _points(reader, METRIC_NORMALIZATION_NEAR_TIES) == {
        _by_resolver("organization"): 2
    }
    assert _points(reader, METRIC_NORMALIZATION_DROPPED) == {
        _by_resolver("schlagwort"): 3
    }


# --- Without OpenTelemetry --------------------------------------------------------


def test_all_helpers_are_noops_without_opentelemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_metrics, "_INSTRUMENTS", None)

    _metrics.record_token_usage(model="m", input_tokens=1, output_tokens=1)
    _metrics.record_gen_ai_operation_duration(1.0, model="m")
    _metrics.record_llm_operation_duration(1.0, operation="extract", model="m")
    _metrics.add_llm_retry(operation="extract", model="m", error_type="E")
    _metrics.record_rate_limiter_wait(1.0)
    _metrics.add_found_entities(1, entity_type="procedure", state="new")
    _metrics.add_submitted_entities(1, entity_type="procedure", status_code=201)
    _metrics.add_skipped_entities(1, entity_type="procedure", reason="r")
    _metrics.add_failed_entities(1, entity_type="procedure", error_type="e")
    _metrics.add_llm_enrichments(1, entity_type="procedure", field="f", source="llm")
    _metrics.record_run_duration(1.0)
    _metrics.add_resolutions({"exact": 1}, resolver="author")
    _metrics.record_match_scores([95.0], resolver="author")
    _metrics.add_near_ties(1, resolver="author")
    _metrics.add_dropped(1, resolver="author")


def test_histogram_falls_back_without_bucket_advisory() -> None:
    class OldMeter:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def create_histogram(self, name: str, **kwargs: Any) -> str:
            if "explicit_bucket_boundaries_advisory" in kwargs:
                raise TypeError("unexpected keyword argument")
            self.calls.append(kwargs)
            return name

    meter = OldMeter()
    result = _metrics._histogram(meter, "x", "s", "d", (1.0,))  # type: ignore[arg-type]
    assert result == "x"
    assert meter.calls == [{"unit": "s", "description": "d"}]
