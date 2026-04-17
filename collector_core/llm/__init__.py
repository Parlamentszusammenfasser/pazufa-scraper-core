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
    ExpertenResult,
    ExpertenResultNoLobbyregister,
    ExtractedExpert,
    ExtractedExpertNoLobbyregister,
    KurztitelResult,
    LineRange,
    MeinungResult,
    SchlagworteResult,
    SectionExtractionResult,
    VerfassungsaenderndResult,
    ZusammenfassungResult,
)
from .prompts import (
    EXPERTEN_PROMPT,
    EXPERTEN_PROMPT_NO_LOBBYREGISTER,
    KURZTITEL_PROMPT,
    MEINUNG_PROMPT,
    SCHLAGWORTE_PROMPT,
    VERFASSUNGSAENDERND_PROMPT,
    ZUSAMMENFASSUNG_GESETZENTWURF_PROMPT,
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
    "ExtractedExpert",
    "ExtractedExpertNoLobbyregister",
    "ExpertenResult",
    "ExpertenResultNoLobbyregister",
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
    "EXPERTEN_PROMPT",
    "EXPERTEN_PROMPT_NO_LOBBYREGISTER",
    "KURZTITEL_PROMPT",
    "ZUSAMMENFASSUNG_PROMPT",
    "ZUSAMMENFASSUNG_GESETZENTWURF_PROMPT",
    "SCHLAGWORTE_PROMPT",
    "MEINUNG_PROMPT",
    "VERFASSUNGSAENDERND_PROMPT",
    "format_sachgebiete_list",
]
