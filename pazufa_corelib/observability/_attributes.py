"""Span, event and attribute names used by pazufa_corelib telemetry.

Standard OpenTelemetry names (GenAI semantic conventions, ``error.type``) are
used where they fit, so backends render corelib and litellm spans with the same
fields. Corelib-specific names live under the ``pazufa.`` namespace.
"""

from typing import Final

# Instrumentation scope / logger names
TRACER_NAME: Final = "pazufa_corelib"
TELEMETRY_LOGGER_NAME: Final = "pazufa_corelib.telemetry"

# Span names
SPAN_LLM_EXTRACT: Final = "pazufa.scraper.llm.extract"
SPAN_LLM_SUMMARIZE: Final = "pazufa.scraper.llm.summarize"
SPAN_LLM_EXTRACT_RELEVANT_SECTION: Final = "pazufa.scraper.llm.extract_relevant_section"

# Event names
EVENT_RETRY: Final = "pazufa.scraper.llm.retry"
EVENT_RATE_LIMIT_WAIT: Final = "pazufa.scraper.llm.rate_limit_wait"

# OpenTelemetry semantic conventions
GEN_AI_REQUEST_MODEL: Final = "gen_ai.request.model"
GEN_AI_USAGE_INPUT_TOKENS: Final = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS: Final = "gen_ai.usage.output_tokens"
ERROR_TYPE: Final = "error.type"

# Corelib-specific attributes
PAZUFA_ATTEMPT: Final = "pazufa.scraper.llm.attempt"
PAZUFA_MAX_RETRIES: Final = "pazufa.scraper.llm.max_retries"
PAZUFA_BACKOFF_SECONDS: Final = "pazufa.scraper.llm.backoff_seconds"
PAZUFA_WAIT_SECONDS: Final = "pazufa.scraper.llm.wait_seconds"
