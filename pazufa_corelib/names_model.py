"""Pydantic models for the author and organisation normalisation chain."""

from pathlib import Path
from typing import Optional, Self, Sequence

import yaml
from pydantic import (
    BaseModel,
    Field,
    FilePath,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

# =====================================================================
# Models for the items
# =====================================================================

_SLUG_RE = r"^[A-ZÄÖÜa-zäöüß0-9][A-ZÄÖÜa-zäöüß0-9\-_]+$"


class BaseName(BaseModel):
    """Base model for Author and Organisation entries."""

    id: str = Field(..., description="Unique slug identifier, e.g. 'mueller-maria'")
    canonical_name: str = Field(
        ..., description="Display form used as the resolved name"
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative spellings, comma-forms, and title variants",
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, value: str) -> str:
        """Validate that the ID is a slug containing only letters, digits, hyphens and underscores.

        Args:
            value: The ID string to validate.

        Returns:
            The validated ID string unchanged.

        Raises:
            ValueError: If the ID contains spaces or disallowed special characters.
        """
        import re

        if not re.match(_SLUG_RE, value):
            raise ValueError(
                f"ID {value!r} must be a slug (letters, digits, hyphens, underscores)"
            )
        return value


class Author(BaseName):
    """Model for a single author (person) entry."""

    pass


class Organisation(BaseName):
    """Model for a single organisation entry."""

    akronym: Optional[str] = Field(
        default=None,
        description="Optional short-form abbreviation, e.g. 'BMF'",
    )


# =====================================================================
# Models for the YAML files
# =====================================================================


class BaseNameFile(BaseModel):
    """Base model for Author and Organisation YAML file validation.

    Subclasses narrow the ``names`` field to the concrete item type.
    """

    source: FilePath
    names: Sequence[BaseName]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "BaseNameFile":
        """Validate that all IDs within the file are unique.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If duplicate IDs are found.
        """
        ids = [entry.id for entry in self.names]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate IDs found in {self.__class__.__name__}"
                f" {self.source}: {duplicates}"
            )
        return self

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """Load and validate a name YAML file from the given path.

        Args:
            path: Path to the YAML file to load.

        Returns:
            A validated instance of the calling class.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the YAML cannot be parsed or validation fails.
        """
        try:
            raw = yaml.safe_load(path.read_text())
        except FileNotFoundError:
            raise FileNotFoundError(f"Name mapping file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse {path.name}: {e}") from e
        try:
            return cls.model_validate({"source": path, **raw})
        except ValidationError as e:
            raise ValueError(f"Validation failed for {path.name}: {e}") from e


class AuthorFile(BaseNameFile):
    """Concrete file model for author YAML files.

    Expected YAML structure::

        names:
          - id: mueller-maria
            canonical_name: Maria Müller
            aliases:
              - Müller, Maria
              - Dr. Maria Müller MdB
    """

    names: list[Author]


class OrganisationFile(BaseNameFile):
    """Concrete file model for organisation YAML files.

    Expected YAML structure::

        names:
          - id: bundesministerium-finanzen
            canonical_name: Bundesministerium der Finanzen
            aliases:
              - Finanzministerium
              - BMF
              - Bundesfinanzministerium
    """

    names: list[Organisation]


# =====================================================================
# Resolution result models
# =====================================================================


class NameIDResolution(BaseModel):
    """Result of a name resolution attempt for a single query.

    Attributes:
        original_name: The raw name string as it appeared in the input.
        resolved_id: The slug ID of the best-matching entry, or the
            original name normalised if no match cleared the threshold.
        canonical_name: The display form of the resolved entry, or the
            original name if unresolved.
        score: Match quality score in [0.0, 100.0]; 0.0 means no match
            cleared the cutoff.
        matched: True if ``score > 0.0``.
        changed: True if the resolved canonical name differs from the
            original input.
    """

    original_name: str
    resolved_id: str
    canonical_name: str
    score: float = Field(..., description="0.0 means no match cleared the cutoff")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def matched(self) -> bool:
        """Return True if the score is above 0.0, indicating a successful match."""
        return self.score > 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def changed(self) -> bool:
        """Return True if the resolved canonical name differs from the original input."""
        return self.original_name != self.canonical_name


class AuthorIDResolution(NameIDResolution):
    """Resolution result for an author query."""

    pass


class OrganisationIDResolution(NameIDResolution):
    """Resolution result for an organisation query."""

    akronym: Optional[str] = Field(
        default=None,
        description="Short-form abbreviation of the resolved organisation, if available",
    )
