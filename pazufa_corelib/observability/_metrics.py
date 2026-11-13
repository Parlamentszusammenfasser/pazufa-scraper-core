"""Metric helpers for the corelib and the scrapers, no-op without OpenTelemetry.

Only depends on ``opentelemetry-api`` (extra ``otel``). Instruments are created
once on a meter obtained at import time; before the application sets up a
``MeterProvider`` (``observability.configure()``) that meter is a proxy, and all
measurements are dropped until then.

Names, units and attributes follow ``_attributes``: OpenTelemetry semantic
conventions where they exist (``gen_ai.client.*``, ``error.type``,
``http.response.status_code``), ``pazufa.*`` otherwise. Every helper sets the
same attribute keys on every call, so series never mix "label set" and "label
missing".
"""

import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._attributes import (
    ENRICHMENT_FIELD,
    ENRICHMENT_SOURCE,
    ENTITY_STATE,
    ENTITY_TYPE,
    ERROR_TYPE,
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_TOKEN_TYPE,
    GEN_AI_TOKEN_TYPE_INPUT,
    GEN_AI_TOKEN_TYPE_OUTPUT,
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
from ._tracing import AttrValue

if TYPE_CHECKING:
    from opentelemetry.metrics import (
        CallbackOptions,
        Counter,
        Histogram,
        Meter,
        Observation,
    )

try:
    from opentelemetry import metrics as _otel_metrics
except ImportError:
    _otel_metrics = None  # type: ignore[assignment]

# Bucket advisories from the GenAI semantic conventions.
TOKEN_BUCKETS: tuple[float, ...] = tuple(float(4**i) for i in range(14))
DURATION_BUCKETS: tuple[float, ...] = tuple(round(0.01 * 2**i, 2) for i in range(14))
# Scraper runs take minutes to hours.
RUN_DURATION_BUCKETS: tuple[float, ...] = (
    10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0, 1800.0, 3600.0, 7200.0, 14400.0
)  # fmt: skip
# Match scores are 0-100 and only recorded for fuzzy matches, which all cleared
# the resolver's threshold (organizations 80, authors and Schlagworte 90). Fine
# buckets above 80 show how much margin the matches have.
MATCH_SCORE_BUCKETS: tuple[float, ...] = (
    80.0, 82.0, 84.0, 86.0, 88.0, 90.0, 92.0, 94.0, 96.0, 98.0, 99.0, 100.0
)  # fmt: skip

DEFAULT_GEN_AI_OPERATION = "chat"
HTTP_ERROR_STATUS_FROM = 400

_last_success: float | None = None


@dataclass(frozen=True)
class _Instruments:
    token_usage: "Histogram"
    gen_ai_operation_duration: "Histogram"
    reasoning_token_usage: "Histogram"
    llm_operation_duration: "Histogram"
    llm_retries: "Counter"
    rate_limiter_wait: "Histogram"
    found_entities: "Counter"
    submitted_entities: "Counter"
    skipped_entities: "Counter"
    failed_entities: "Counter"
    llm_enrichments: "Counter"
    run_duration: "Histogram"
    normalization_resolutions: "Counter"
    normalization_match_score: "Histogram"
    normalization_near_ties: "Counter"
    normalization_dropped: "Counter"


def _histogram(
    meter: "Meter", name: str, unit: str, description: str, buckets: Sequence[float]
) -> "Histogram":
    try:
        return meter.create_histogram(
            name,
            unit=unit,
            description=description,
            explicit_bucket_boundaries_advisory=buckets,
        )
    except TypeError:  # opentelemetry-api without bucket advisories
        return meter.create_histogram(name, unit=unit, description=description)


def _observe_last_success(options: "CallbackOptions") -> Iterable["Observation"]:
    from opentelemetry.metrics import Observation

    if _last_success is None:
        return []
    return [Observation(_last_success)]


def _create_instruments(meter: "Meter") -> _Instruments:
    meter.create_observable_gauge(
        METRIC_SCRAPER_RUN_LAST_SUCCESS,
        callbacks=[_observe_last_success],
        unit="s",
        description="Unix time of the last successful scraper run.",
    )
    return _Instruments(
        token_usage=_histogram(
            meter,
            METRIC_GEN_AI_TOKEN_USAGE,
            "{token}",
            "Number of input and output tokens used per provider call.",
            TOKEN_BUCKETS,
        ),
        gen_ai_operation_duration=_histogram(
            meter,
            METRIC_GEN_AI_OPERATION_DURATION,
            "s",
            "Duration of a single provider call.",
            DURATION_BUCKETS,
        ),
        reasoning_token_usage=_histogram(
            meter,
            METRIC_LLM_REASONING_TOKEN_USAGE,
            "{token}",
            "Reasoning tokens per provider call; already part of the output tokens.",
            TOKEN_BUCKETS,
        ),
        llm_operation_duration=_histogram(
            meter,
            METRIC_LLM_OPERATION_DURATION,
            "s",
            "Duration of a corelib LLM operation, including retries and waits.",
            DURATION_BUCKETS,
        ),
        llm_retries=meter.create_counter(
            METRIC_LLM_RETRIES, unit="{retry}", description="Retried LLM calls."
        ),
        rate_limiter_wait=_histogram(
            meter,
            METRIC_LLM_RATE_LIMITER_WAIT_DURATION,
            "s",
            "Time spent waiting for the local LLM rate limiter.",
            DURATION_BUCKETS,
        ),
        found_entities=meter.create_counter(
            METRIC_SCRAPER_FOUND_ENTITIES,
            unit="{entity}",
            description="Entities found in the source.",
        ),
        submitted_entities=meter.create_counter(
            METRIC_SCRAPER_SUBMITTED_ENTITIES,
            unit="{entity}",
            description="Entities submitted to the PaZuFa API.",
        ),
        skipped_entities=meter.create_counter(
            METRIC_SCRAPER_SKIPPED_ENTITIES,
            unit="{entity}",
            description="Entities deliberately not submitted.",
        ),
        failed_entities=meter.create_counter(
            METRIC_SCRAPER_FAILED_ENTITIES,
            unit="{entity}",
            description="Entities that could not be processed.",
        ),
        llm_enrichments=meter.create_counter(
            METRIC_SCRAPER_LLM_ENRICHMENTS,
            unit="{enrichment}",
            description="LLM enrichment results per field.",
        ),
        run_duration=_histogram(
            meter,
            METRIC_SCRAPER_RUN_DURATION,
            "s",
            "Duration of a scraper run.",
            RUN_DURATION_BUCKETS,
        ),
        normalization_resolutions=meter.create_counter(
            METRIC_NORMALIZATION_RESOLUTIONS,
            unit="{resolution}",
            description="Name and ID resolutions by resolver and outcome.",
        ),
        normalization_match_score=_histogram(
            meter,
            METRIC_NORMALIZATION_MATCH_SCORE,
            "1",
            "Score (0-100) of fuzzy name and ID matches.",
            MATCH_SCORE_BUCKETS,
        ),
        normalization_near_ties=meter.create_counter(
            METRIC_NORMALIZATION_NEAR_TIES,
            unit="{resolution}",
            description="Resolutions whose two best candidates scored almost equal.",
        ),
        normalization_dropped=meter.create_counter(
            METRIC_NORMALIZATION_DROPPED,
            unit="{name}",
            description="Unresolved values dropped because of strict=True.",
        ),
    )


_INSTRUMENTS: _Instruments | None = (
    _create_instruments(_otel_metrics.get_meter(TRACER_NAME))
    if _otel_metrics is not None
    else None
)


def _with_error(
    attributes: dict[str, AttrValue], error_type: str | None
) -> dict[str, AttrValue]:
    if error_type is not None:
        attributes[ERROR_TYPE] = error_type
    return attributes


def _merged(
    extra: Mapping[str, AttrValue] | None, attributes: dict[str, AttrValue]
) -> dict[str, AttrValue]:
    # Schema attributes win over caller extras with the same key.
    return {**extra, **attributes} if extra else attributes


# --- LLM (corelib) -------------------------------------------------------------


def record_token_usage(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int = 0,
    operation_name: str = DEFAULT_GEN_AI_OPERATION,
    provider: str | None = None,
) -> None:
    """Record the token usage of one provider call.

    Counts of 0 are skipped: they mostly mean the provider reported no usage,
    and recording them would distort the distribution.

    Args:
        model: Requested model, ``gen_ai.request.model``.
        input_tokens: Prompt tokens.
        output_tokens: Completion tokens, including reasoning tokens.
        reasoning_tokens: Reasoning part of ``output_tokens``; recorded on its
            own metric so ``sum()`` over token usage does not count it twice.
        operation_name: ``gen_ai.operation.name``, ``"chat"`` for completions.
        provider: ``gen_ai.provider.name``, e.g. ``"openai"``, if known.
    """
    if _INSTRUMENTS is None:
        return
    attributes: dict[str, AttrValue] = {
        GEN_AI_OPERATION_NAME: operation_name,
        GEN_AI_REQUEST_MODEL: model,
    }
    if provider is not None:
        attributes[GEN_AI_PROVIDER_NAME] = provider
    for token_type, count in (
        (GEN_AI_TOKEN_TYPE_INPUT, input_tokens),
        (GEN_AI_TOKEN_TYPE_OUTPUT, output_tokens),
    ):
        if count > 0:
            _INSTRUMENTS.token_usage.record(
                count, {**attributes, GEN_AI_TOKEN_TYPE: token_type}
            )
    if reasoning_tokens > 0:
        _INSTRUMENTS.reasoning_token_usage.record(reasoning_tokens, attributes)


def record_gen_ai_operation_duration(
    seconds: float,
    *,
    model: str,
    error_type: str | None = None,
    operation_name: str = DEFAULT_GEN_AI_OPERATION,
    provider: str | None = None,
) -> None:
    """Record the duration of one provider call.

    Args:
        seconds: Call duration.
        model: Requested model, ``gen_ai.request.model``.
        error_type: Exception class name or provider error code on failure.
        operation_name: ``gen_ai.operation.name``, ``"chat"`` for completions.
        provider: ``gen_ai.provider.name``, if known.
    """
    if _INSTRUMENTS is None:
        return
    attributes: dict[str, AttrValue] = {
        GEN_AI_OPERATION_NAME: operation_name,
        GEN_AI_REQUEST_MODEL: model,
    }
    if provider is not None:
        attributes[GEN_AI_PROVIDER_NAME] = provider
    _INSTRUMENTS.gen_ai_operation_duration.record(
        seconds, _with_error(attributes, error_type)
    )


def record_llm_operation_duration(
    seconds: float, *, operation: str, model: str, error_type: str | None = None
) -> None:
    """Record the duration of a corelib LLM operation including retries.

    Args:
        seconds: Operation duration.
        operation: ``pazufa.llm.operation``, e.g. ``"extract"``.
        model: Requested model.
        error_type: Error class name if the operation failed.
    """
    if _INSTRUMENTS is None:
        return
    attributes: dict[str, AttrValue] = {
        LLM_OPERATION: operation,
        GEN_AI_REQUEST_MODEL: model,
    }
    _INSTRUMENTS.llm_operation_duration.record(
        seconds, _with_error(attributes, error_type)
    )


def add_llm_retry(*, operation: str, model: str, error_type: str) -> None:
    """Count one retried LLM call.

    Args:
        operation: ``pazufa.llm.operation``, e.g. ``"extract"``.
        model: Requested model.
        error_type: Error class name that triggered the retry.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.llm_retries.add(
        1,
        {LLM_OPERATION: operation, GEN_AI_REQUEST_MODEL: model, ERROR_TYPE: error_type},
    )


def record_rate_limiter_wait(seconds: float) -> None:
    """Record time spent waiting for the local LLM rate limiter.

    Args:
        seconds: Wait duration.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.rate_limiter_wait.record(seconds)


# --- Scraper ---------------------------------------------------------------------


def add_found_entities(
    count: int,
    *,
    entity_type: str,
    state: str,
    attributes: Mapping[str, AttrValue] | None = None,
) -> None:
    """Count entities found in the source.

    Args:
        count: Number of entities; 0 is recorded so the series exists.
        entity_type: ``pazufa.entity.type``, e.g. ``"procedure"``.
        state: ``pazufa.entity.state``: ``new``, ``retried``, ``changed``,
            ``cached``.
        attributes: Extra attributes such as ``pazufa.election_period``.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.found_entities.add(
        count, _merged(attributes, {ENTITY_TYPE: entity_type, ENTITY_STATE: state})
    )


def add_submitted_entities(
    count: int,
    *,
    entity_type: str,
    status_code: int,
    attributes: Mapping[str, AttrValue] | None = None,
) -> None:
    """Count entities submitted to the PaZuFa API.

    Following the HTTP conventions, a status code of 400 or above also sets
    ``error.type`` to the status code, so rejections are found via
    ``error.type`` like every other error.

    Args:
        count: Number of entities.
        entity_type: ``pazufa.entity.type``.
        status_code: HTTP status code of the API response.
        attributes: Extra attributes such as ``pazufa.election_period``.
    """
    if _INSTRUMENTS is None:
        return
    error_type = str(status_code) if status_code >= HTTP_ERROR_STATUS_FROM else None
    _INSTRUMENTS.submitted_entities.add(
        count,
        _merged(
            attributes,
            _with_error(
                {ENTITY_TYPE: entity_type, HTTP_RESPONSE_STATUS_CODE: status_code},
                error_type,
            ),
        ),
    )


def add_skipped_entities(
    count: int,
    *,
    entity_type: str,
    reason: str,
    attributes: Mapping[str, AttrValue] | None = None,
) -> None:
    """Count entities deliberately not submitted.

    Args:
        count: Number of entities.
        entity_type: ``pazufa.entity.type``.
        reason: ``pazufa.skip.reason``, a fixed category like ``"out_of_scope"``.
        attributes: Extra attributes such as ``pazufa.election_period``.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.skipped_entities.add(
        count, _merged(attributes, {ENTITY_TYPE: entity_type, SKIP_REASON: reason})
    )


def add_failed_entities(
    count: int,
    *,
    entity_type: str,
    error_type: str,
    attributes: Mapping[str, AttrValue] | None = None,
) -> None:
    """Count entities that could not be processed.

    Args:
        count: Number of entities.
        entity_type: ``pazufa.entity.type``.
        error_type: ``error.type``, a fixed category like ``"not_found"``.
        attributes: Extra attributes such as ``pazufa.election_period``.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.failed_entities.add(
        count, _merged(attributes, {ENTITY_TYPE: entity_type, ERROR_TYPE: error_type})
    )


def add_llm_enrichments(
    count: int,
    *,
    entity_type: str,
    field: str,
    source: str,
    error_type: str | None = None,
    attributes: Mapping[str, AttrValue] | None = None,
) -> None:
    """Count LLM enrichment results.

    Args:
        count: Number of enrichments.
        entity_type: ``pazufa.entity.type``.
        field: ``pazufa.enrichment.field``, e.g. ``"Kurztitel"``.
        source: ``pazufa.enrichment.source``: ``"llm"`` or ``"cache"``.
        error_type: Set if the enrichment failed.
        attributes: Extra attributes such as ``pazufa.election_period``.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.llm_enrichments.add(
        count,
        _merged(
            attributes,
            _with_error(
                {
                    ENTITY_TYPE: entity_type,
                    ENRICHMENT_FIELD: field,
                    ENRICHMENT_SOURCE: source,
                },
                error_type,
            ),
        ),
    )


def record_run_duration(seconds: float, *, error_type: str | None = None) -> None:
    """Record the duration of a scraper run.

    Args:
        seconds: Run duration.
        error_type: Set if the run failed.
    """
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.run_duration.record(seconds, _with_error({}, error_type))


def set_run_last_success(timestamp: float | None = None) -> None:
    """Mark the run as successful; reported as ``pazufa.scraper.run.last_success``.

    Call it only after a successful run. A crashed or killed run never reports
    it, which is what the "no successful run" alert relies on.

    Args:
        timestamp: Unix time; defaults to now.
    """
    global _last_success
    _last_success = time.time() if timestamp is None else timestamp


# --- Normalization (corelib) -------------------------------------------------------
# Called once per batch with aggregated values, not once per name: the resolvers
# run in loops over every Vorgang.


def add_resolutions(counts: Mapping[str, int], *, resolver: str) -> None:
    """Count the resolutions of one batch by outcome.

    Outcomes with a count of 0 are skipped.

    Args:
        counts: Number of resolutions per ``pazufa.normalization.outcome``:
            ``exact``, ``fuzzy`` or ``unresolved``, e.g. a
            ``collections.Counter``.
        resolver: ``pazufa.normalization.resolver``, e.g. ``"author"``.
    """
    if _INSTRUMENTS is None:
        return
    for outcome, count in counts.items():
        if count > 0:
            _INSTRUMENTS.normalization_resolutions.add(
                count,
                {NORMALIZATION_RESOLVER: resolver, NORMALIZATION_OUTCOME: outcome},
            )


def record_match_scores(scores: Iterable[float], *, resolver: str) -> None:
    """Record the scores of the fuzzy matches of one batch.

    Pass only fuzzy matches: exact matches always score 100 and unresolved ones
    0, so they would only hide the distribution near the threshold.

    Args:
        scores: Match scores in the range 0-100.
        resolver: ``pazufa.normalization.resolver``, e.g. ``"organization"``.
    """
    if _INSTRUMENTS is None:
        return
    attributes: dict[str, AttrValue] = {NORMALIZATION_RESOLVER: resolver}
    for score in scores:
        _INSTRUMENTS.normalization_match_score.record(score, attributes)


def add_near_ties(count: int, *, resolver: str) -> None:
    """Count resolutions whose two best candidates scored almost equal.

    Args:
        count: Number of near-ties; 0 is skipped.
        resolver: ``pazufa.normalization.resolver``.
    """
    if _INSTRUMENTS is None or count <= 0:
        return
    _INSTRUMENTS.normalization_near_ties.add(count, {NORMALIZATION_RESOLVER: resolver})


def add_dropped(count: int, *, resolver: str) -> None:
    """Count unresolved values dropped because of ``strict=True``.

    Args:
        count: Number of dropped values; 0 is skipped.
        resolver: ``pazufa.normalization.resolver``.
    """
    if _INSTRUMENTS is None or count <= 0:
        return
    _INSTRUMENTS.normalization_dropped.add(count, {NORMALIZATION_RESOLVER: resolver})
