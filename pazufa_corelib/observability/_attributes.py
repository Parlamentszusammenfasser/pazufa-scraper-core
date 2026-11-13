"""Telemetry names used by pazufa_corelib and the scrapers built on it.

OpenTelemetry-native naming: existing semantic conventions (``gen_ai.*``,
``error.type``, ``http.*``, ``service.*``, ``deployment.*``) are used wherever
they fit. Everything specific to PaZuFa lives under the ``pazufa.`` prefix and
follows the same rules: dot-separated lowercase namespaces, ``snake_case`` for
multi-word components, units in the instrument's ``unit`` and never in the name,
no ``_total``, plural metric names only for countable units like ``{entity}``.

The GenAI conventions are still in "development" status, so their names may
change; keeping every name here makes that a one-file change.
"""

from typing import Final

# --- Instrumentation scope and logger ---------------------------------------
TRACER_NAME: Final = "pazufa_corelib"
TELEMETRY_LOGGER_NAME: Final = "pazufa_corelib.telemetry"

# --- Resource attributes (set once per process) ------------------------------
SERVICE_NAMESPACE: Final = "service.namespace"  # "pazufa"
SERVICE_NAME: Final = "service.name"  # e.g. "pazufa-scraper"
SERVICE_VERSION: Final = "service.version"  # image / package version
SERVICE_INSTANCE_ID: Final = "service.instance.id"  # UUIDv5 of the scraper ID
DEPLOYMENT_ENVIRONMENT_NAME: Final = "deployment.environment.name"
PAZUFA_SCRAPER_ID: Final = "pazufa.scraper.id"  # scraper UUID
PAZUFA_PARLIAMENT: Final = "pazufa.parliament"  # e.g. "BW", "BT"

# --- Span names ----------------------------------------------------------------
SPAN_LLM_EXTRACT: Final = "pazufa.llm.extract"
SPAN_LLM_SUMMARIZE: Final = "pazufa.llm.summarize"
SPAN_LLM_EXTRACT_RELEVANT_SECTION: Final = "pazufa.llm.extract_relevant_section"

# --- Span event names ----------------------------------------------------------
EVENT_LLM_RETRY: Final = "pazufa.llm.retry"
EVENT_LLM_RATE_LIMITED: Final = "pazufa.llm.rate_limited"

# --- Semantic-convention attributes --------------------------------------------
ERROR_TYPE: Final = "error.type"
HTTP_RESPONSE_STATUS_CODE: Final = "http.response.status_code"
GEN_AI_OPERATION_NAME: Final = "gen_ai.operation.name"
GEN_AI_PROVIDER_NAME: Final = "gen_ai.provider.name"
GEN_AI_REQUEST_MODEL: Final = "gen_ai.request.model"
GEN_AI_TOKEN_TYPE: Final = "gen_ai.token.type"
GEN_AI_TOKEN_TYPE_INPUT: Final = "input"
GEN_AI_TOKEN_TYPE_OUTPUT: Final = "output"
GEN_AI_USAGE_INPUT_TOKENS: Final = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS: Final = "gen_ai.usage.output_tokens"
EXCEPTION_MESSAGE: Final = "exception.message"

# --- PaZuFa attributes: LLM ----------------------------------------------------
LLM_OPERATION: Final = "pazufa.llm.operation"  # "extract", "summarize", ...
LLM_ATTEMPT: Final = "pazufa.llm.attempt"  # 1-based
LLM_MAX_RETRIES: Final = "pazufa.llm.max_retries"
LLM_RETRY_DELAY: Final = "pazufa.llm.retry.delay"  # seconds
LLM_RATE_LIMITER_DELAY: Final = "pazufa.llm.rate_limiter.delay"  # seconds

# --- PaZuFa attributes: LLM log fields -----------------------------------------
# Structured ``extra`` fields of the LLMConnector logs. No name is a prefix of
# another (OpenTelemetry naming rule), hence e.g. token_estimate.total.
LLM_API_KEY_SET: Final = "pazufa.llm.api_key_set"
LLM_TIMEOUT: Final = "pazufa.llm.timeout"  # seconds
LLM_RESPONSE_MODEL: Final = "pazufa.llm.response_model"
LLM_VALIDATION_RETRIES: Final = "pazufa.llm.validation_retries"
LLM_PROMPT_CHARS: Final = "pazufa.llm.prompt.chars"
LLM_INPUT_CHARS: Final = "pazufa.llm.input.chars"  # source text to summarize
LLM_OUTPUT_CHARS: Final = "pazufa.llm.output.chars"
LLM_MAPPED_ERROR_TYPE: Final = "pazufa.llm.error.mapped_type"  # connector class
LLM_RETRY_CAPPED_DELAY: Final = "pazufa.llm.retry.capped_delay"  # seconds
LLM_RETRY_JITTER: Final = "pazufa.llm.retry.jitter"  # seconds
LLM_TOKEN_ESTIMATE_INPUT: Final = "pazufa.llm.token_estimate.input"
LLM_TOKEN_ESTIMATE_OUTPUT_BUFFER: Final = "pazufa.llm.token_estimate.output_buffer"
LLM_TOKEN_ESTIMATE_TOTAL: Final = "pazufa.llm.token_estimate.total"
LLM_RATE_LIMITER_ENABLED: Final = "pazufa.llm.rate_limiter.enabled"
LLM_RATE_LIMITER_CALLS: Final = "pazufa.llm.rate_limiter.calls"  # in window
LLM_RATE_LIMITER_MAX_CALLS: Final = "pazufa.llm.rate_limiter.max_calls"
LLM_RATE_LIMITER_TOKENS: Final = "pazufa.llm.rate_limiter.tokens"  # in window
LLM_RATE_LIMITER_MAX_TOKENS: Final = "pazufa.llm.rate_limiter.max_tokens"
LLM_RATE_LIMITER_WINDOW: Final = "pazufa.llm.rate_limiter.window"  # seconds
LLM_RATE_LIMITER_EXPIRED_SLOTS: Final = "pazufa.llm.rate_limiter.expired_slots"
LLM_SUMMARY_LANGUAGE: Final = "pazufa.llm.summary.language"
LLM_SUMMARY_MAX_SENTENCES: Final = "pazufa.llm.summary.max_sentences"
LLM_SUMMARY_MAX_WORDS: Final = "pazufa.llm.summary.max_words"
LLM_SUMMARY_MAX_CHARACTERS: Final = "pazufa.llm.summary.max_characters"
LLM_CHUNK_COUNT: Final = "pazufa.llm.chunk.count"
LLM_CHUNK_INDEX: Final = "pazufa.llm.chunk.index"  # 1-based
LLM_CHUNK_SIZE: Final = "pazufa.llm.chunk.size"  # tokens
LLM_CHUNK_OVERLAP: Final = "pazufa.llm.chunk.overlap"  # tokens
LLM_CHUNK_LINE_START: Final = "pazufa.llm.chunk.line_start"  # 1-based
LLM_CHUNK_LINE_END: Final = "pazufa.llm.chunk.line_end"  # 1-based, inclusive
LLM_CHUNK_CONSECUTIVE_IRRELEVANT: Final = "pazufa.llm.chunk.consecutive_irrelevant"
LLM_LINES_EXTRACTED: Final = "pazufa.llm.lines.extracted"
LLM_LINES_TOTAL: Final = "pazufa.llm.lines.total"
# Invalid constructor or call arguments that fall back to a default or None
LLM_CONFIG_PARAMETER: Final = "pazufa.llm.config.parameter"  # e.g. "max_retries"
LLM_CONFIG_VALUE: Final = "pazufa.llm.config.value"  # repr() of the given value
LLM_CONFIG_DEFAULT: Final = "pazufa.llm.config.default"  # value used instead

# --- PaZuFa attributes: scraper domain -----------------------------------------
ENTITY_TYPE: Final = "pazufa.entity.type"  # procedure, document, session, ...
ENTITY_STATE: Final = "pazufa.entity.state"  # new, retried, changed, cached
SKIP_REASON: Final = "pazufa.skip.reason"  # out_of_scope, ...
ENRICHMENT_FIELD: Final = "pazufa.enrichment.field"  # Kurztitel, Ressort, ...
ENRICHMENT_SOURCE: Final = "pazufa.enrichment.source"  # llm, cache
ELECTION_PERIOD: Final = "pazufa.election_period"
PROCEDURE_TRACK: Final = "pazufa.procedure.track"

# --- Metrics: LLM (recorded by the corelib) ------------------------------------
# Histogram {token}; gen_ai.token.type, gen_ai.request.model,
# gen_ai.operation.name, gen_ai.provider.name
METRIC_GEN_AI_TOKEN_USAGE: Final = "gen_ai.client.token.usage"
# Histogram s, per provider call; as above plus error.type on failure
METRIC_GEN_AI_OPERATION_DURATION: Final = "gen_ai.client.operation.duration"
# Histogram {token}; separate because reasoning tokens are part of "output"
METRIC_LLM_REASONING_TOKEN_USAGE: Final = "pazufa.llm.reasoning_token.usage"
# Histogram s, whole operation incl. retries; pazufa.llm.operation, error.type
METRIC_LLM_OPERATION_DURATION: Final = "pazufa.llm.operation.duration"
# Counter {retry}; error.type
METRIC_LLM_RETRIES: Final = "pazufa.llm.retries"
# Histogram s
METRIC_LLM_RATE_LIMITER_WAIT_DURATION: Final = "pazufa.llm.rate_limiter.wait.duration"

# --- Metrics: scraper (names shared here, recorded by the scrapers) ------------
# Counters {entity}; pazufa.entity.type plus the attributes noted
METRIC_SCRAPER_FOUND_ENTITIES: Final = "pazufa.scraper.found.entities"  # state
# http.response.status_code; error.type only when rejected
METRIC_SCRAPER_SUBMITTED_ENTITIES: Final = "pazufa.scraper.submitted.entities"
METRIC_SCRAPER_SKIPPED_ENTITIES: Final = "pazufa.scraper.skipped.entities"  # reason
METRIC_SCRAPER_FAILED_ENTITIES: Final = "pazufa.scraper.failed.entities"  # error.type
# Counter {enrichment}; pazufa.enrichment.field/.source, error.type
METRIC_SCRAPER_LLM_ENRICHMENTS: Final = "pazufa.scraper.llm.enrichments"
# Histogram s, one point per run; error.type when the run failed
METRIC_SCRAPER_RUN_DURATION: Final = "pazufa.scraper.run.duration"
# Gauge s (Unix time), set only after a successful run
METRIC_SCRAPER_RUN_LAST_SUCCESS: Final = "pazufa.scraper.run.last_success"

# --- PaZuFa attributes: normalization ------------------------------------------
# Fixed categories only: never the raw or resolved name (cardinality, personal data)
NORMALIZATION_RESOLVER: Final = "pazufa.normalization.resolver"  # author, ...
NORMALIZATION_OUTCOME: Final = "pazufa.normalization.outcome"  # exact, fuzzy, ...
NORMALIZATION_RESOLVER_AUTHOR: Final = "author"
NORMALIZATION_RESOLVER_ORGANIZATION: Final = "organization"
NORMALIZATION_RESOLVER_SCHLAGWORT: Final = "schlagwort"
NORMALIZATION_RESOLVER_SACHGEBIET: Final = "sachgebiet"
NORMALIZATION_OUTCOME_EXACT: Final = "exact"
NORMALIZATION_OUTCOME_FUZZY: Final = "fuzzy"
NORMALIZATION_OUTCOME_UNRESOLVED: Final = "unresolved"

# --- Metrics: normalization (recorded by the corelib) --------------------------
# Counter {resolution}; pazufa.normalization.resolver, pazufa.normalization.outcome
METRIC_NORMALIZATION_RESOLUTIONS: Final = "pazufa.normalization.resolutions"
# Histogram, unit "1" (score 0-100), fuzzy matches only; pazufa.normalization.resolver
METRIC_NORMALIZATION_MATCH_SCORE: Final = "pazufa.normalization.match.score"
# Counter {resolution}; pazufa.normalization.resolver
METRIC_NORMALIZATION_NEAR_TIES: Final = "pazufa.normalization.near_ties"
# Counter {name}, values dropped with strict=True; pazufa.normalization.resolver
METRIC_NORMALIZATION_DROPPED: Final = "pazufa.normalization.dropped"
