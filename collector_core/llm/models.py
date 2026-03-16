"""Pydantic response models for LLM enrichment.

Each model is designed to be used standalone with ``LLMConnector.extract()``.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .sachgebiete_taxonomy import SACHGEBIETE_SET


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
            "Sachgebiete from the provided list that are relevant" " to this document/station."
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
    def validate_sachgebiete(cls, v: list[str]) -> list[str]:
        """Deduplicate and reject invalid Sachgebiete so Instructor triggers a retry."""
        v = list(dict.fromkeys(v))
        invalid = [sg for sg in v if sg not in SACHGEBIETE_SET]
        if invalid:
            raise ValueError(
                f"Invalid Sachgebiete (not in taxonomy): {invalid}. "
                "Use only terms from the provided list."
            )
        return v


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


class VerfassungsaenderndResult(BaseModel):
    """Whether a Gesetzentwurf amends the state constitution."""

    ist_verfassungsaendernd: bool = Field(
        description="True if this law amends the state constitution (Landesverfassung).",
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
            raise ValueError(
                "is_relevant is True but relevant_lines is empty"
            )
        return self
