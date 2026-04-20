"""Schlagwort vocabulary loading, merging, and resolution.

Provides :class:`SchlagwortResolver`, which loads Tags and Sachgebiete from
YAML files, merges them into a single vocabulary, and exposes:

- JSON representations for LLM prompt injection
- Pydantic ``Annotated`` types (``TagList``, ``SachgebietList``,
  ``SachgebieteNumberList``) for use as field types in response models
- Lookup helpers for converting between Sachgebiet IDs and
  Sachgebiet numbers
"""

import json
import logging
import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

from corelib.schlagworte_model import (
    Sachgebiet,
    SachgebietFile,
    SchlagwortIDResolution,
    Tag,
    TagFile,
)
from pydantic import AfterValidator, BaseModel
from rapidfuzz import fuzz
from rapidfuzz.process import cdist

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

GLOBAL_TAGS_FILES: list[Path] = [MAPPINGS_DIR.joinpath("global_tags.yaml")]
"""Constant list of the paths to the global tag files."""
SACHGEBIETE_FILES: list[Path] = [MAPPINGS_DIR.joinpath("sachgebiete.yaml")]
"""Constant list of the paths to the sachgebiet files."""

logger = logging.getLogger(__name__)

_EXACT_MATCH_THRESHOLD: float = 100.0
_FUZZY_MATCH_THRESHOLD: float = 90.0

_RE_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

# =====================================================================
# private helper functions
# =====================================================================


def _load_global_tag_ids() -> set[str]:
    """Load the canonical tag IDs from all global tag files."""
    return {
        tag.id for path in GLOBAL_TAGS_FILES for tag in TagFile.from_path(path).tags
    }


def _processor_ids(input_id_text: str) -> str:
    """Normalize and clean an ID string for fuzzy comparison.

    Performs Unicode normalization, lowercases, strips whitespace, and removes
    punctuation. ``normalise_volltext()`` is intentionally not used due to its
    higher performance cost.

    Args:
        input_id_text: The input string to be processed.

    Returns:
        The processed and standardized identifier string.
    """
    id_text = unicodedata.normalize("NFKC", input_id_text)  # ü stays ü, ﬁ → fi
    id_text = id_text.lower().strip()
    id_text = _RE_PUNCT.sub("", id_text)
    return id_text


def _canonicalise_ids(
    raw_ids: list[str],
    canonical_ids: list[str],
    strict: bool = False,
    cutoff: float = _FUZZY_MATCH_THRESHOLD,
) -> list[SchlagwortIDResolution]:
    # C++ Matrix call
    matrix = cdist(
        raw_ids,
        canonical_ids,
        scorer=fuzz.token_sort_ratio,
        processor=_processor_ids,
        score_cutoff=cutoff,  # scores below cutoff → 0.0
    )

    result: list[SchlagwortIDResolution] = []

    for i, raw_id in enumerate(raw_ids):
        row = matrix[i]
        best_idx: int = row.argmax()
        best_score: float = row[best_idx]

        if 0.0 == best_score:
            if not strict:
                result.append(
                    SchlagwortIDResolution(
                        original_id=raw_id, resolved_id=raw_id, score=0.0
                    )
                )

        else:
            resolved_id = canonical_ids[best_idx]
            result.append(
                SchlagwortIDResolution(
                    original_id=raw_id, resolved_id=resolved_id, score=best_score
                )
            )

    return result


def _load_tags(local_tags: list[Path] | None = None) -> list[Tag]:
    """Load and merge Tags and Sachgebiete from files into a single list of Tags.

    Files are merged in the following order, where later entries override earlier ones:

    1. Local tags (caller-supplied, lowest priority)
    2. Global tags (GLOBAL_TAGS_FILES)
    3. Sachgebiete (SACHGEBIETE_FILES, highest priority)

    Local tag IDs are canonicalised against the global tag vocabulary in a single
    batch call to :func:`_canonicalise_ids` before being merged.

    Returns a deduplicated list of Tags keyed by id.
    """
    tag_list: dict[str, Tag] = {}
    local_paths: list[Path] = local_tags or []

    if local_paths:
        local_tag_objects: list[Tag] = []
        for path in local_paths:
            local_tag_objects.extend(TagFile.from_path(path).tags)

        canonical_ids: list[str] = list(_load_global_tag_ids())
        raw_ids: list[str] = [tag.id for tag in local_tag_objects]
        resolutions = _canonicalise_ids(raw_ids, canonical_ids)
        id_map: dict[str, str] = {r.original_id: r.resolved_id for r in resolutions}

        for tag in local_tag_objects:
            resolved_id = id_map[tag.id]
            if resolved_id != tag.id:
                logger.debug("Canonical local tag %r -> %r", tag.id, resolved_id)
            tag_list[resolved_id] = Tag.model_construct(
                id=resolved_id,
                description=tag.description,
            )

    for path in GLOBAL_TAGS_FILES:
        for tag in TagFile.from_path(path).tags:
            tag_list[tag.id] = tag

    for path in SACHGEBIETE_FILES:  # last-write-wins
        for sachgebiet in SachgebietFile.from_path(path).tags:
            tag_list[sachgebiet.id] = Tag.model_construct(
                id=sachgebiet.id,
                description=sachgebiet.description,
            )

    return list(tag_list.values())


def _load_sachgebiete() -> list[Sachgebiet]:
    """Load Sachgebiete from all sachgebiet files and return a deduplicated list.

    Raises:
        ValueError: If the same Sachgebiet number appears in more than one file.
    """
    sachgebiet_list: dict[str, Sachgebiet] = {}
    number_index: dict[int, tuple[str, Path]] = {}  # number -> (id, source path)

    for path in SACHGEBIETE_FILES:
        sachgebiet_file = SachgebietFile.from_path(path)
        for sachgebiet in sachgebiet_file.tags:
            if sachgebiet.number in number_index:
                existing_id, existing_path = number_index[sachgebiet.number]
                raise ValueError(
                    f"Duplicate Sachgebiet number {sachgebiet.number}: "
                    f"{existing_id!r} in {existing_path} "
                    f"conflicts with {sachgebiet.id!r} in {path}"
                )
            number_index[sachgebiet.number] = (sachgebiet.id, path)
            sachgebiet_list[sachgebiet.id] = sachgebiet

    return list(sachgebiet_list.values())


def _build_json(items: Sequence[BaseModel]) -> str:
    """Serialize a list of Pydantic models to a JSON string.

    Args:
        items: Models to serialize. Logs a debug message if the list is empty.

    Raises:
        ValueError: If any item cannot be serialized.
    """
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
    """Serialize Sachgebiete to JSON, omitting the Sachgebiet number."""
    return _build_json(
        [Tag.model_construct(id=s.id, description=s.description) for s in sachgebiete]
    )


def _make_validated_list(valid: set, error_msg: str) -> Any:
    """Build an Annotated list type that rejects values not in *valid*."""

    def validate(v: list) -> list:
        if invalid := set(v) - valid:
            raise ValueError(f"{error_msg}: {invalid}")
        return v

    return Annotated[list, AfterValidator(validate)]


# =====================================================================
# SchlagwortResolver
# =====================================================================


class SchlagwortResolver:
    """Resolves, merges and provides access to the global Schlagwort vocabulary.

    Load order (later entries override earlier ones):
    1. Local tags (caller-supplied, lowest priority)
    2. Global tags (GLOBAL_TAGS_FILES)
    3. Sachgebiete (SACHGEBIETE_FILES, highest priority)

    The local lists of the tags and sachgebiete are generated in this class's
    constructor. They are generated fresh for each construction. This is done
    to prevent stale tag or sachgebiet lists in the scraper.
    """

    def __init__(self, local_tags: list[Path] | None = None) -> None:
        # load vocabulary
        self._tags: list[Tag] = _load_tags(local_tags)
        self._sachgebiete: list[Sachgebiet] = _load_sachgebiete()

        # pre-serialise JSON representations
        self._tags_json: str = _build_json(self._tags)
        self._sachgebiete_json: str = _build_json(self._sachgebiete)
        self._sachgebiete_no_numbers_json: str = _build_json_sachgebiete_no_numbers(
            self._sachgebiete
        )

        # build lookup indices
        self._tag_ids: set[str] = {t.id for t in self._tags}
        self._tag_ids_list: list[str] = list(self._tag_ids)
        self._sachgebiete_id_to_number: dict[str, int] = {
            s.id: s.number for s in self._sachgebiete
        }
        self._sachgebiete_ids_list: list[str] = list(self._sachgebiete_id_to_number)
        self._sachgebiete_number_to_id: dict[int, str] = {
            s.number: s.id for s in self._sachgebiete
        }

        # pre-build annotated types for use as Pydantic field types
        self.SachgebietList: Any = _make_validated_list(
            set(self._sachgebiete_id_to_number), "Invalid Sachgebiete"
        )
        self.SachgebieteNumberList: Any = _make_validated_list(
            set(self._sachgebiete_number_to_id), "Invalid Sachgebiet-Nummern"
        )
        self.TagList: Any = _make_validated_list(self._tag_ids, "Invalid Tags")

    # =====================================================================
    # Tag actions
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
        return tag_id in self._tag_ids

    def fuzzy_check_tag(self, tag_id: str) -> bool:
        """Fuzzy-match a tag ID against the known vocabulary.

        Uses :func:`_canonicalise_ids` to find the best fuzzy match.

        Args:
            tag_id: The raw tag ID to check.

        Returns:
            True if the ID matched a known tag above the fuzzy cutoff, False otherwise.
        """
        check_id = _canonicalise_ids([tag_id], self._tag_ids_list)[0]
        logger.debug("Fuzzy check returned: %s", check_id)
        # explicitly typed for mypy
        return bool(check_id.matched)

    def canonicalise_tags(self, tag_ids: list[str], strict: bool = False) -> list[str]:
        """Canonicalise a list of tag IDs against the known vocabulary.

        Args:
            tag_ids: Raw tag IDs to resolve.
            strict: If True, unmatched IDs are dropped; if False, they are
                returned unchanged.

        Returns:
            List of resolved canonical tag IDs.
        """
        resolved_ids = _canonicalise_ids(tag_ids, self._tag_ids_list, strict)
        return [r.resolved_id for r in resolved_ids]

    # =====================================================================
    # Sachgebiet actions
    # =====================================================================

    def get_sachgebiete_json(self) -> str:
        """Return the full Sachgebiet vocabulary including numbers as a JSON string.

        Returns:
            JSON string containing the full Sachgebiet vocabulary.
        """
        return self._sachgebiete_json

    def get_sachgebiete_no_numbers_json(self) -> str:
        """Return the Sachgebiet vocabulary without Sachgebiet numbers as JSON.

        Returns:
            JSON string containing Sachgebiet id and description only.
        """
        return self._sachgebiete_no_numbers_json

    def get_sachgebiet_number(self, sachgebiet_id: str) -> int:
        """Return the Sachgebiet number for a given Sachgebiet ID.

        Args:
            sachgebiet_id: The canonical Sachgebiet id to look up.

        Returns:
            The Sachgebiet number.

        Raises:
            KeyError: If the id is not found in the vocabulary.
        """
        nummer = self._sachgebiete_id_to_number.get(sachgebiet_id)
        if nummer is None:
            raise KeyError(f"Sachgebiet ID {sachgebiet_id!r} not found")
        return nummer

    def get_sachgebiet_id(self, sachgebiet_number: int) -> str:
        """Return the Sachgebiet id for a given Sachgebiet number.

        Args:
            sachgebiet_number: The Sachgebiet number to look up.

        Returns:
            The canonical Sachgebiet id.

        Raises:
            KeyError: If the number is not found in the vocabulary.
        """
        sachgebiet_id = self._sachgebiete_number_to_id.get(sachgebiet_number)
        if sachgebiet_id is None:
            raise KeyError(f"Sachgebiet number {sachgebiet_number!r} not found")
        return sachgebiet_id

    def check_sachgebiet_id(self, sachgebiet_id: str) -> bool:
        """Check whether a given id corresponds to a known Sachgebiet.

        Args:
            sachgebiet_id: The Sachgebiet id to check.

        Returns:
            True if the id matches a known Sachgebiet, False otherwise.
        """
        return sachgebiet_id in self._sachgebiete_id_to_number

    def check_sachgebiet_nummer(self, sachgebiet_nummer: int) -> bool:
        """Check whether a given number corresponds to a known Sachgebiet.

        Args:
            sachgebiet_nummer: The Sachgebiet number to check.

        Returns:
            True if the number matches a known Sachgebiet, False otherwise.
        """
        return sachgebiet_nummer in self._sachgebiete_number_to_id

    def canonicalise_sachgebiete(self, sachgebiet_ids: list[str]) -> list[str]:
        """Canonicalise a list of Sachgebiet IDs against the known vocabulary.

        Unmatched IDs are dropped (strict mode).

        Args:
            sachgebiet_ids: Raw Sachgebiet IDs to resolve.

        Returns:
            List of resolved canonical Sachgebiet IDs.
        """
        resolved_ids = _canonicalise_ids(
            sachgebiet_ids, self._sachgebiete_ids_list, True
        )
        return [r.resolved_id for r in resolved_ids]
