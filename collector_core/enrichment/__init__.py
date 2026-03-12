"""Shared LLM enrichment models, taxonomy, and prompt templates."""

from .models import (
    KurztitelResult,
    MeinungResult,
    SchlagworteResult,
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
    # Models
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
