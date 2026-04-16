import re
from pathlib import Path
from typing import Optional, Self, Sequence

import yaml
from pydantic import (
    BaseModel,
    Field,
    FilePath,
    PositiveInt,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

"""Models for the validation in the tags and sachgebiete normalization chain."""


# =====================================================================
#  Models for the items
# =====================================================================


class BaseSchlagwort(BaseModel):
    """Basemodel for Tag and Sachgebiet validation."""

    id: str = Field(..., description="Name of the Tag or Sachgebiet")
    description: Optional[str] = Field(
        default=None,
        description=(
            "Optional description of the Tag or Sachgebiet for human and LLM context."
        ),
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, value: str) -> str:
        """Validate that the ID contains only letters, spaces, and hyphens.

        Args:
            value: The ID string to validate.

        Returns:
            The validated ID string unchanged.

        Raises:
            ValueError: If the ID contains numbers or special characters.
        """
        if not re.match(r"^[A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß\s\-]+$", value):
            raise ValueError(
                f"{cls.__class__.__name__}-ID of {value!r} cannot contain"
                " number or special characters"
            )
        return value


# The following is written to make Tag and Sachgebiet Models siblings.
# This is done to have conformity in the Core-lib.
class Tag(BaseSchlagwort):
    """Model for Tag validation."""

    pass


class Sachgebiet(BaseSchlagwort):
    """Model for Sachgebiet validation.

    Extends BaseSchlagwort with the Sachgebiet number.
    """

    number: PositiveInt = Field(..., description="Number of the Sachgebiet")


# =====================================================================
# Models for the files containing the items
# =====================================================================


class BaseSchlagwortFile(BaseModel):
    """Base model for Tag and Sachgebiet file validation.

    Subclasses narrow the ``tags`` field.
    """

    source: FilePath
    tags: Sequence[BaseSchlagwort]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "BaseSchlagwortFile":
        """Validate that all tag IDs in the file are unique.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If duplicate IDs are found.
        """
        ids = [tag.id for tag in self.tags]
        duplicates = {id for id in ids if ids.count(id) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate IDs found in {self.__class__.__name__}"
                f" {self.source}: {duplicates}"
            )
        return self

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """Load and validate a Tag or Sachgebiet YAML file from the given path.

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
            raise FileNotFoundError(f"Global tag file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse {path.name}: {e}") from e
        try:
            return cls.model_validate({"source": path, **raw})
        except ValidationError as e:
            raise ValueError(f"Validation failed for {path.name}: {e}") from e


class TagFile(BaseSchlagwortFile):
    """Concrete file model for Tag YAML files."""

    tags: list[Tag]


class SachgebietFile(BaseSchlagwortFile):
    """Concrete file model for Sachgebiet YAML files."""

    tags: list[Sachgebiet]

    @model_validator(mode="after")
    def validate_unique_numbers(self) -> "SachgebietFile":
        """Validate that all Sachgebiet numbers in the file are unique.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If duplicate Sachgebiet numbers are found.
        """
        nrs = [t.number for t in self.tags]
        duplicates = {nr for nr in nrs if nrs.count(nr) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate Sachgebiet numbers found in {self.source}: {duplicates}"
            )
        return self


# =====================================================================
# Model for fuzzy check of Schlagworte
# =====================================================================


class SchlagwortIDResolution(BaseModel):
    """Result of a fuzzy ID resolution attempt for a single Schlagwort.

    Attributes:
        original_id: The raw ID as it appeared in the input.
        resolved_id: The best-matching ID found in the reference list.
        score: Match quality score; 0.0 means no match cleared the cutoff.
        changed: True if resolved_id differs from original_id.
        matched: True if the score is above 0.0, indicating a successful match.
    """

    original_id: str
    resolved_id: str
    score: float = Field(..., description="0.0 means no match cleared cutoff")

    @computed_field  # Since pydantic 2.0.3 this is allowed. (Pycharm displays error)
    @property
    def changed(self) -> bool:
        """Return True if the resolved ID differs from the original ID."""
        return self.original_id != self.resolved_id

    @computed_field
    @property
    def matched(self) -> bool:
        """Return True if the score is above 0.0, indicating a successful match."""
        return self.score > 0.0
