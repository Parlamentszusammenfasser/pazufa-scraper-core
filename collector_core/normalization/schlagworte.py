import json
import logging
from pathlib import Path
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel

from collector_core.schlagworte_model import (
    Sachgebiet,
    SachgebietFile,
    Tag,
    TagFile,
)

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

GLOBAL_TAGS_FILES: list[Path] = [MAPPINGS_DIR.joinpath("global_tags.yaml")]
"""Constant list of the paths to the global tag files."""
SACHGEBIETE_FILES: list[Path] = [MAPPINGS_DIR.joinpath("sachgebiete.yaml")]
"""Constant list of the paths to the sachgebiet files."""

logger = logging.getLogger(__name__)


# =====================================================================
# private helper functions
# =====================================================================


def _load_global_tag_ids() -> set[str]:
    """Load the canonical tag IDs from all global tag files."""
    return {
        tag.id for path in GLOBAL_TAGS_FILES for tag in TagFile.from_path(path).tags
    }


def _canonicalise_id(tag_id: str, canonical_ids: set[str]) -> str:
    """Return the canonical id if an exact case-insensitive match exists.

    Returns as-is if no match is found.
    """
    lookup = {c.lower(): c for c in canonical_ids}
    return lookup.get(tag_id.lower(), tag_id)


def _load_tags(local_tags: list[Path] | None = None) -> list[Tag]:
    """Load and merge Tags and Sachgebiete from files into a single list of Tags.

    Files are merged in the following order, where later entries override earlier ones:

    1. Local tags (caller-supplied, lowest priority)
    2. Global tags (GLOBAL_TAGS_FILES)
    3. Sachgebiete (SACHGEBIETE_FILES, highest priority)

    Returns a deduplicated list of Tags keyed by id.
    """
    tag_list: dict[str, Tag] = {}
    local_paths: list[Path] = local_tags or []

    if local_paths:
        canonical_ids = _load_global_tag_ids()
        for path in local_paths:
            validated = TagFile.from_path(path)
            for tag in validated.tags:
                canonical_id = _canonicalise_id(tag.id, canonical_ids)
                if canonical_id != tag.id:
                    logger.debug("Canonical local tag %r -> %r", tag.id, canonical_id)
                tag_list[canonical_id] = Tag.model_construct(
                    id=canonical_id,
                    description=tag.description,
                )

    for path in GLOBAL_TAGS_FILES:
        validated = TagFile.from_path(path)
        for tag in validated.tags:
            tag_list[tag.id] = tag

    for path in SACHGEBIETE_FILES:  # last-write-wins
        validated = SachgebietFile.from_path(path)
        for sachgebiet in validated.tags:
            tag_list[sachgebiet.id] = Tag.model_construct(
                id=sachgebiet.id,
                description=sachgebiet.description,
            )

    return list(tag_list.values())


def _load_sachgebiete() -> list[Sachgebiet]:
    sachgebiet_list: dict[str, Sachgebiet] = {}
    number_index: dict[int, tuple[str, Path]] = {}  # number -> (id, source path)

    for path in SACHGEBIETE_FILES:
        validated = SachgebietFile.from_path(path)
        for sachgebiet in validated.tags:
            # validation already performed by SachgebietFile.from_path
            if sachgebiet.number in number_index:
                existing_id, existing_path = number_index[sachgebiet.number]
                raise ValueError(
                    f"Duplicate Parlamentsspiegel number {sachgebiet.number}: "
                    f"{existing_id!r} in {existing_path} "
                    f"conflicts with {sachgebiet.id!r} in {path}"
                )
            number_index[sachgebiet.number] = (sachgebiet.id, path)
            sachgebiet_list[sachgebiet.id] = sachgebiet

    return list(sachgebiet_list.values())


def _build_json(items: list[BaseModel]) -> str:
    if not items:
        logger.debug("_build_json called with empty list")
    try:
        return json.dumps(
            [item.model_dump() for item in items],
            ensure_ascii=False,
            indent=2,
        )
    except TypeError as e:
        raise ValueError(
            f"Failed to serialize {type(items[0]).__name__} items to JSON: {e}"
        ) from e


def _build_json_sachgebiete_no_numbers(sachgebiete: list[Sachgebiet]) -> str:
    return _build_json(
        [Tag.model_construct(id=s.id, description=s.description) for s in sachgebiete]
    )


class Schlagwort_Resolver:
    """Resolves, merges and provides access to the global Schlagwort vocabulary.

    Load order (later entries override earlier ones):
    1. Local tags (caller-supplied, lowest priority)
    2. Global tags (GLOBAL_TAGS_FILES)
    3. Sachgebiete (SACHGEBIETE_FILES, highest priority)

    The local lists of the tags and sachgebiete are generated in this class's
    constructor. They are generated fresh for each construction. This is done
    to prevent stale tag or sachgebiet lists in the scraper.
    """

    def __init__(self, local_tags: Optional[list[Path]] = None) -> None:
        # generating of lists of Objects
        self._tags: list[Tag] = _load_tags(local_tags)
        self._sachgebiete: list[Sachgebiet] = _load_sachgebiete()

        # building JSON
        self._tags_json: str = _build_json(self._tags)
        self._sachgebiete_json: str = _build_json(self._sachgebiete)
        self._sachgebiete_no_numbers_json: str = _build_json_sachgebiete_no_numbers(
            self._sachgebiete
        )

        # building lookup indices
        self._sachgebiete_id_to_number: dict[str, int] = {
            s.id: s.number for s in self._sachgebiete
        }
        self._sachgebiete_number_to_id: dict[int, str] = {
            s.number: s.id for s in self._sachgebiete
        }

        # pre-build annotated types
        self.SachgebietList: type = self._make_sachgebiet_list()
        self.SachgebieteNumberList: type = self._make_sachgebiet_number_list()
        self.TagList: type = self._make_tag_list()

    # =====================================================================
    # Model Extensions
    # =====================================================================

    def _make_sachgebiet_list(self) -> type:
        valid_ids = {s.id for s in self._sachgebiete}

        def validate(v: list[str]) -> list[str]:
            invalid = set(v) - valid_ids
            if invalid:
                raise ValueError(f"Invalid Sachgebiete: {invalid}")
            return v

        return Annotated[list[str], AfterValidator(validate)]

    def _make_sachgebiet_number_list(self) -> type:
        valid_numbers = {s.number for s in self._sachgebiete}

        def validate(v: list[int]) -> list[int]:
            invalid = set(v) - valid_numbers
            if invalid:
                raise ValueError(f"Invalide Sachgebiet-Nummern: {invalid}")
            return v

        return Annotated[list[int], AfterValidator(validate)]

    def _make_tag_list(self) -> type:
        valid_ids = {t.id for t in self._tags}

        def validate(v: list[str]) -> list[str]:
            invalid = set(v) - valid_ids
            if invalid:
                raise ValueError(f"Ungültige Tags: {invalid}")
            return v

        return Annotated[list[str], AfterValidator(validate)]

    # =====================================================================
    # tag Actions
    # =====================================================================

    def get_tags_json(self) -> str:
        """Return the full tag vocabulary as a JSON string.

        Includes global tags, Sachgebiete (converted to Tags, numbers excluded)
        and local tags if provided at construction time.

        Returns:
            JSON string containing the full merged tag vocabulary.
        """
        return self._tags_json

    def check_tag(self, tag_id: str) -> bool:
        """Check whether a given id corresponds to a known tag.

        Args:
            tag_id: The tag id to check.

        Returns:
            True if the id matches a known tag, False otherwise.
        """
        return any(tag.id == tag_id for tag in self._tags)

    def get_tags_npy():
        """Not implemented."""
        pass



    # =====================================================================
    # Sachgebiet Actions
    # =====================================================================

    def get_sachgebiete_json(self):
        """Return the full Sachgebiet vocabulary including the numbers as a JSON string.

        Returns:
            JSON string containing the full Sachgebiet vocabulary.
        """
        return self._sachgebiete_json

    def get_sachgebiete_no_numbers_json(self):
        """Return the full Sachgebiet vocabulary excluding the numbers as a JSON string.

        Returns:
            JSON string containing the full Sachgebiet vocabulary.
        """
        return self._sachgebiete_no_numbers_json

    def get_sachgebiet_number(self, sachgebiet_id: str) -> int:
        """Return the Sachgebiet number for a given Sachgebiet ID.

        Args:
            sachgebiet_id: The canonical Sachgebiet id to look up.

        Returns:
            The Sachgebiet number, or None if the id is not found.
        """
        nummer = self._sachgebiete_id_to_number.get(sachgebiet_id)
        if nummer is None:
            raise KeyError(f"Sachgebiet ID {sachgebiet_id!r} not found")
        return nummer


    def get_sachgebiet_id(self, sachgebiet_number: int) -> str:
        """Return the Sachgebiet id for a given Sachgebiet number.

        Args:
            sachgebiet_number: The number of the Sachgebiet to look up.

        Returns:
            The Sachgebiet id, or None if the number is not found.
        """
        id = self._sachgebiete_number_to_id.get(sachgebiet_number)
        if id is None:
            raise KeyError(f"Sachgebiet number {sachgebiet_number!r} not found")
        return id

    def check_sachgebiet_id(self, sachgebiet_id: str) -> bool:
        """Check whether a given id corresponds to a known Sachgebiet.

        Args:
            sachgebiet_id: The Sachgebiet id to check.

        Returns:
            True if the id matches a known Sachgebiet, False otherwise.
        """
        return sachgebiet_id in self._id_to_number

    def check_sachgebiet_nummer(self, sachgebiet_nummer: int) -> bool:
        """Check whether a given number corresponds to a known Sachgebiet.

        Args:
            sachgebiet_nummer: The Parlamentsspiegel number to check.

        Returns:
            True if the number matches a known Sachgebiet, False otherwise.
        """
        return sachgebiet_nummer in self._number_to_id