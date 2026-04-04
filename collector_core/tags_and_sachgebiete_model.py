from _pytest._code import source
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    PositiveInt,
    FilePath,
)
from typing import Optional, Sequence
import re

"""Models for the validation in the tags and sachgebiete normalization chain."""


# =====================================================================
#  Models for the items
# =====================================================================


class BaseTag(BaseModel):
    """Basemodel for Tag and Sachgebiet validation"""

    id: str = Field(..., description="Name of the Tag or Sachgebiet")
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the Tag or Sachgebiet for human and LLM context.",
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, value: str) -> str:
        if not re.match(r"^[A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß\s\-]+$", value):
            raise ValueError(
                f"{cls.__class__.__name__}-ID of {value!r} cannot contain number or special characters"
            )
        return value


# The following is written to make Tag and Sachgebiet Models siblings.
# This is done to have conformity in the Core-lib.
class Tag(BaseTag):
    """Model for Tag validation"""

    pass


class Sachgebiet(BaseTag):
    """Model for Sachgebiet validation,extends BaseTag with number of the Sachgebiet"""

    number: PositiveInt = Field(..., description="Number of the Sachgebiet")


# =====================================================================
# Models for the files containing the items
# =====================================================================


class BaseTagFile(BaseModel):
    """Base model for Tag and Sachgebiet file validation. Subclasses narrow the `tags` field."""

    source: FilePath
    tags: Sequence[BaseTag]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "BaseTagFile":
        ids = [tag.id for tag in self.tags]
        duplicates = {id for id in ids if ids.count(id) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate IDs found in {self.__class__.__name__} {self.source}: {duplicates}"
            )
        return self


class TagFile(BaseTagFile):
    tags: list[Tag]


class SachgebietFile(BaseTagFile):
    tags: list[Sachgebiet]

    @model_validator(mode="after")
    def validate_unique_numbers(self) -> "SachgebietFile":
        nrs = [t.number for t in self.tags]
        duplicates = {nr for nr in nrs if nrs.count(nr) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate Sachgebiet numbers found in {self.source}: {duplicates}"
            )
        return self
