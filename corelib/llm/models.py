"""Pydantic response models for LLM enrichment.

Each model is designed to be used standalone with ``LLMConnector.extract()``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

if TYPE_CHECKING:
    from corelib.normalization.schlagworte import SchlagwortResolver

LOGGER = logging.getLogger(__name__)


class KurztitelResult(BaseModel):
    """Short title for a Vorgang."""

    kurztitel: str = Field(
        min_length=1, description="Short, descriptive title (5-10 words) in German."
    )


class ZusammenfassungResult(BaseModel):
    """Summary of a parliamentary document."""

    zusammenfassung: str = Field(
        min_length=1, description="150-250 word summary of the document in German."
    )


class SchlagworteResult(BaseModel):
    """Per-station keywords derived from document text.

    Two fields: sachgebiete (from the Parlamentsspiegel taxonomy) and
    schlagworte (free-form keywords for topics not covered by Sachgebiete).
    """

    sachgebiete: list[str] = Field(
        description=(
            "Sachgebiete from the provided list that are relevant"
            " to this document/station."
        ),
    )
    schlagworte: list[str] = Field(
        description=(
            "3-7 additional lowercase keywords for specific topics"
            " not covered by the Sachgebiete."
        ),
    )

    @field_validator("sachgebiete")
    @classmethod
    def validate_sachgebiete(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Deduplicate and canonicalise Sachgebiete via SchlagwortResolver.

        When a ``SchlagwortResolver`` is provided via Pydantic's
        ``validation_context`` (key ``"resolver"``), each raw Sachgebiet ID
        is fuzzy-matched against the canonical vocabulary. Unmatched entries
        are dropped (strict mode) and a warning is logged.

        Without a resolver in the context the field is only deduplicated.
        """
        v = list(dict.fromkeys(v))
        if not v:
            return v

        ctx = info.context
        resolver: SchlagwortResolver | None = ctx.get("resolver") if ctx else None
        if resolver is None:
            return v

        canonicalised = resolver.canonicalise_sachgebiete(v)
        dropped = set(v) - set(canonicalised)
        if dropped:
            LOGGER.warning(
                "Dropped unmatched Sachgebiete during validation: %s",
                dropped,
            )
        return list(dict.fromkeys(canonicalised))


class MeinungResult(BaseModel):
    """Opinion/stance score for a parliamentary document."""

    meinung: Literal[1, 2, 3, 4, 5] = Field(
        description=(
            "Meinungsbild: 1=Ablehnung, 2=überwiegend kritisch,"
            " 3=gemischt/neutral, 4=überwiegend zustimmend, 5=Zustimmung"
        ),
    )
    begruendung: str = Field(
        min_length=1,
        description="Brief reasoning for the score, in German (1-2 sentences).",
    )


class ExtractedExpert(BaseModel):
    """A single author or submitting party extracted from a parliamentary document."""

    person: str | None = Field(
        default=None,
        description=(
            "Name der Person (z.B. 'Prof. Dr. Susanne Meyer'). "
            "None wenn nur eine Organisation ohne benannte Person."
        ),
    )
    organisation: str = Field(
        min_length=1,
        description=(
            "Name der Organisation oder Institution "
            "(z.B. 'Deutscher Gewerkschaftsbund', 'Universität Heidelberg'). "
            "Bei Einzelpersonen ohne Organisation den Kontext angeben "
            "(z.B. 'Sachverständiger', 'Privatperson')."
        ),
    )
    fachgebiet: str | None = Field(
        default=None,
        description=(
            "Fachgebiet oder Expertise der Person/Organisation "
            "(z.B. 'Verfassungsrecht', 'Arbeitsmarktpolitik')."
        ),
    )
    lobbyregister: str | None = Field(
        default=None,
        description=(
            "Lobbyregister-Eintrag falls im Dokument genannt — entweder als "
            "vollständige URL oder als Registernummer "
            "(z.B. 'https://www.lobbyregister.bundestag.de/...', 'R001234',"
            " 'DEBYLT000D'). "
            "Nur ausfüllen wenn explizit im Dokument angegeben."
        ),
    )


class ExpertenResult(BaseModel):
    """Extracted authors/submitting parties from a Stellungnahme or Beschlussempfehlung.

    Wraps a list of ExtractedExpert entries (at least one required).
    """

    experten: list[ExtractedExpert] = Field(
        min_length=1,
        description=(
            "Liste aller identifizierbaren Autoren oder einreichenden Parteien."
        ),
    )


class ExtractedExpertNoLobbyregister(BaseModel):
    """A single author or submitting party without lobby register field.

    Used when lobbyregister extraction is disabled to prevent hallucination.
    """

    person: str | None = Field(
        default=None,
        description=(
            "Name der Person (z.B. 'Prof. Dr. Susanne Meyer'). "
            "None wenn nur eine Organisation ohne benannte Person."
        ),
    )
    organisation: str = Field(
        min_length=1,
        description=(
            "Name der Organisation oder Institution "
            "(z.B. 'Deutscher Gewerkschaftsbund', 'Universität Heidelberg'). "
            "Bei Einzelpersonen ohne Organisation den Kontext angeben "
            "(z.B. 'Sachverständiger', 'Privatperson')."
        ),
    )
    fachgebiet: str | None = Field(
        default=None,
        description=(
            "Fachgebiet oder Expertise der Person/Organisation "
            "(z.B. 'Verfassungsrecht', 'Arbeitsmarktpolitik')."
        ),
    )


class ExpertenResultNoLobbyregister(BaseModel):
    """Extracted authors without lobby register field.

    Use this model when lobbyregister extraction is disabled in your scraper
    to prevent the LLM from hallucinating register entries that don't exist.
    """

    experten: list[ExtractedExpertNoLobbyregister] = Field(
        min_length=1,
        description=(
            "Liste aller identifizierbaren Autoren oder einreichenden Parteien."
        ),
    )


class VerfassungsaenderndResult(BaseModel):
    """Whether a Gesetzentwurf amends the state constitution."""

    ist_verfassungsaendernd: bool = Field(
        description=(
            "True if this law amends the state constitution (Landesverfassung)."
        ),
    )
    begruendung: str = Field(
        min_length=1,
        description="Brief reasoning for the determination, in German.",
    )


class LineRange(BaseModel):
    """A contiguous range of line numbers in a text chunk."""

    start: int = Field(ge=1, description="First relevant line number (inclusive).")
    end: int = Field(ge=1, description="Last relevant line number (inclusive).")

    @model_validator(mode="after")
    def start_le_end(self) -> "LineRange":
        """Ensure start <= end."""
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) must be <= end ({self.end})")
        return self


class SectionExtractionResult(BaseModel):
    """Result of checking a text chunk for relevant content.

    The LLM returns line number ranges pointing into the numbered input text.
    Actual text extraction is done computationally from the source to guarantee
    verbatim output.
    """

    is_relevant: bool = Field(
        description="Whether the chunk contains text relevant to the Vorgang."
    )
    relevant_lines: list[LineRange] = Field(
        default_factory=list,
        description="Line ranges containing relevant text (empty if not relevant).",
    )

    @model_validator(mode="after")
    def relevant_implies_lines(self) -> "SectionExtractionResult":
        """Ensure is_relevant=True comes with at least one line range."""
        if self.is_relevant and not self.relevant_lines:
            raise ValueError("is_relevant is True but relevant_lines is empty")
        return self

    @model_validator(mode="after")
    def lines_within_chunk(self, info: "ValidationInfo") -> "SectionExtractionResult":
        """Reject line ranges that fall outside the input chunk.

        Requires ``min_line`` and ``max_line`` in the Pydantic
        *validation_context*.  When no context is provided the check
        is skipped silently so the model stays usable in tests and
        other callers that don't supply chunk boundaries.
        """
        ctx = info.context
        if not ctx or "min_line" not in ctx or "max_line" not in ctx:
            return self
        min_line: int = ctx["min_line"]
        max_line: int = ctx["max_line"]
        for lr in self.relevant_lines:
            if lr.start < min_line or lr.end > max_line:
                raise ValueError(
                    f"Line range [{lr.start}-{lr.end}] is outside the "
                    f"input chunk [{min_line}-{max_line}]. "
                    f"Only return lines within the provided text."
                )
        return self
