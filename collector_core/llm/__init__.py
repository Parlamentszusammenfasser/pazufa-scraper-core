"""Shared LLM enrichment models, taxonomy, prompt templates, and connector."""

from .llm_connector import (
    LLMAuthenticationError,
    LLMConnector,
    LLMConnectorError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTemporaryProviderError,
    LLMValidationError,
)
from .models import (
    KurztitelResult,
    LineRange,
    MeinungResult,
    SchlagworteResult,
    SectionExtractionResult,
    VerfassungsaenderndResult,
    ZusammenfassungResult,
)
from .prompts import (
    KURZTITEL_PROMPT,
    MEINUNG_PROMPT,
    SCHLAGWORTE_PROMPT,
    VERFASSUNGSAENDERND_PROMPT,
    ZUSAMMENFASSUNG_PROMPT,
    format_sachgebiete_list,
)
from .sachgebiete_taxonomy import SACHGEBIETE, SACHGEBIETE_NAMES, SACHGEBIETE_SET

__all__ = [
    # LLM Connector
    "LLMConnector",
    "LLMConnectorError",
    "LLMProviderError",
    "LLMAuthenticationError",
    "LLMQuotaExceededError",
    "LLMRateLimitError",
    "LLMTemporaryProviderError",
    "LLMValidationError",
    # Models
    "KurztitelResult",
    "ZusammenfassungResult",
    "SchlagworteResult",
    "MeinungResult",
    "VerfassungsaenderndResult",
    "LineRange",
    "SectionExtractionResult",
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
