"""Shared LLM enrichment models, prompt templates, and connector."""

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
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

_LAZY_CONNECTOR_NAMES: frozenset[str] = frozenset(
    {
        "LLMConnector",
        "LLMConnectorError",
        "LLMProviderError",
        "LLMAuthenticationError",
        "LLMQuotaExceededError",
        "LLMRateLimitError",
        "LLMTemporaryProviderError",
        "LLMValidationError",
    }
)


def __getattr__(name: str) -> Any:
    """Import connector symbols (and litellm) on first access.

    Args:
        name: Attribute name looked up on this package.

    Returns:
        The requested connector symbol.

    Raises:
        AttributeError: If ``name`` is not a lazily exported symbol.
    """
    if name in _LAZY_CONNECTOR_NAMES:
        from . import llm_connector

        value = getattr(llm_connector, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
