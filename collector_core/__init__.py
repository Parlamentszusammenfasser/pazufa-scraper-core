"""
collector_core - Core library for collecting parliamentary data
"""

from .enrichment import (
    KURZTITEL_PROMPT,
    MEINUNG_PROMPT,
    SACHGEBIETE,
    SACHGEBIETE_NAMES,
    SACHGEBIETE_SET,
    SCHLAGWORTE_PROMPT,
    VERFASSUNGSAENDERND_PROMPT,
    ZUSAMMENFASSUNG_PROMPT,
    KurztitelResult,
    MeinungResult,
    SchlagworteResult,
    VerfassungsaenderndResult,
    ZusammenfassungResult,
    format_sachgebiete_list,
)
from .llm_connector import (
    LLMAuthenticationError,
    LLMConnector,
    LLMConnectorError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponseParseError,
    LLMTemporaryProviderError,
    LLMValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # LLM Connector
    "LLMConnector",
    "LLMConnectorError",
    "LLMResponseParseError",
    "LLMProviderError",
    "LLMAuthenticationError",
    "LLMQuotaExceededError",
    "LLMRateLimitError",
    "LLMTemporaryProviderError",
    "LLMValidationError",
    # Enrichment models
    "KurztitelResult",
    "ZusammenfassungResult",
    "SchlagworteResult",
    "MeinungResult",
    "VerfassungsaenderndResult",
    # Taxonomy
    "SACHGEBIETE",
    "SACHGEBIETE_NAMES",
    "SACHGEBIETE_SET",
    # Prompts
    "KURZTITEL_PROMPT",
    "ZUSAMMENFASSUNG_PROMPT",
    "SCHLAGWORTE_PROMPT",
    "MEINUNG_PROMPT",
    "VERFASSUNGSAENDERND_PROMPT",
    "format_sachgebiete_list",
]
