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

from pydantic import AfterValidator, BaseModel
from rapidfuzz import fuzz, process

from pazufa_corelib.normalization._fuzzy import fuzzy_resolve
from pazufa_corelib.schlagworte_model import (
    RESERVED_SCHLAGWORT_IDS,
    Sachgebiet,
    SachgebietFile,
    SchlagwortIDResolution,
    Tag,
    TagFile,
)

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

_GLOBAL_TAGS_FILES: tuple[Path, ...] = (MAPPINGS_DIR.joinpath("global_tags.yaml"),)
"""Constant tuple of the paths to the global tag files."""
_SACHGEBIETE_FILES: tuple[Path, ...] = (MAPPINGS_DIR.joinpath("sachgebiete.yaml"),)
"""Constant tuple of the paths to the sachgebiet files."""

LOGGER = logging.getLogger(__name__)

_EXACT_MATCH_THRESHOLD: float = 100.0
_FUZZY_MATCH_THRESHOLD: float = 90.0
_NEAR_TIE_EPSILON: float = 1.0

_RE_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

# =====================================================================
# private helper functions
# =====================================================================


def _load_global_tag_ids() -> set[str]:
    """Load the canonical tag IDs from all global tag files."""
    return {
        tag.id for path in _GLOBAL_TAGS_FILES for tag in TagFile.from_path(path).tags
    }


def _processor_ids(input_id_text: str) -> str:
    """Normalize and clean an ID string for fuzzy comparison.

    Performs Unicode normalization, lowercases, strips whitespace, and removes
    punctuation. ``normalize_volltext()`` is intentionally not used due to its
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
    near_tie_epsilon: float = _NEAR_TIE_EPSILON,
) -> list[SchlagwortIDResolution]:
    """Fuzzy-match raw IDs against canonical IDs and return resolutions.

    Each raw ID is matched to its closest canonical ID using token-sort-ratio
    scoring. Near-tie matches are logged as warnings.

    Args:
        raw_ids: IDs to resolve.
        canonical_ids: Accepted IDs to match against.
        strict: If True, drop raw IDs that fall below the cutoff.
            If False, keep them unchanged.
        cutoff: Minimum fuzzy-match score; scores below are treated as 0.
        near_tie_epsilon: Score difference within which two candidates are
            considered a near-tie and logged as a warning.

    Returns:
        A list of SchlagwortIDResolution with the original ID, resolved ID,
        and match score.

    Raises:
        ValueError: If raw_ids or canonical_ids is empty.
    """
    pairs = fuzzy_resolve(
        raw_ids,
        canonical_ids,
        scorer=fuzz.token_sort_ratio,
        processor=_processor_ids,
        cutoff=cutoff,
        strict=strict,
        near_tie_epsilon=near_tie_epsilon,
    )
    return [
        SchlagwortIDResolution(original_id=o, resolved_id=r, score=s)
        for o, r, s in pairs
    ]


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
                LOGGER.debug("Canonical local tag %r -> %r", tag.id, resolved_id)
            tag_list[resolved_id] = Tag.model_construct(
                id=resolved_id,
                description=tag.description,
            )

    for path in _GLOBAL_TAGS_FILES:
        for tag in TagFile.from_path(path).tags:
            tag_list[tag.id] = tag

    for path in _SACHGEBIETE_FILES:  # last-write-wins
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

    for path in _SACHGEBIETE_FILES:
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
        LOGGER.debug("_build_json called with empty list")
    try:
        return json.dumps(
            [item.model_dump() for item in items],
            ensure_ascii=False,
            indent=2,
        )
    except TypeError as e:
        sample_type = type(items[0]).__name__ if items else None
        context = f" ({sample_type} items)" if sample_type else ""
        raise ValueError(f"Failed to serialize items to JSON{context}: {e}") from e


def _build_json_sachgebiete_no_numbers(sachgebiete: list[Sachgebiet]) -> str:
    """Serialize Sachgebiete to JSON, omitting the Sachgebiet number.

    Reserved catch-alls (`Unbekannt`, `ohne@-Systematik`) are dropped: this
    feeds the classification prompt, and offering them as choices invites the
    model to label a document "unknown" instead of picking a real Sachgebiet.
    They stay in the vocabulary for round-tripping values the API sends us.
    """
    return _build_json(
        [
            Tag.model_construct(id=s.id, description=s.description)
            for s in sachgebiete
            if s.id not in RESERVED_SCHLAGWORT_IDS
        ]
    )


def _make_validated_list(valid: set, error_msg: str) -> Any:
    """Build an Annotated list type that rejects values not in *valid*."""

    def validate(v: list) -> list:
        """Raise ValueError if any element in *v* is not in the valid set."""
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

    def __init__(
        self,
        local_tags: list[Path] | None = None,
        match_threshold: float = _FUZZY_MATCH_THRESHOLD,
        near_tie_epsilon: float = _NEAR_TIE_EPSILON,
    ) -> None:
        self._match_threshold = match_threshold
        self._near_tie_epsilon = near_tie_epsilon
        # load vocabulary
        self._tags: list[Tag] = _load_tags(local_tags)
        self._sachgebiete: list[Sachgebiet] = _load_sachgebiete()

        # pre-serialize JSON representations
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

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "SchlagwortResolver initialised",
                extra={
                    "local_tag_files_count": len(local_tags) if local_tags else 0,
                    "tags_count": len(self._tags),
                    "sachgebiete_count": len(self._sachgebiete),
                },
            )

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
        check_id = _canonicalise_ids(
            [tag_id],
            self._tag_ids_list,
            cutoff=self._match_threshold,
            near_tie_epsilon=self._near_tie_epsilon,
        )[0]
        LOGGER.debug("Fuzzy check returned: %s", check_id)
        # explicitly typed for mypy
        return bool(check_id.matched)

    def canonicalise_tags(self, tag_ids: list[str], strict: bool = False) -> list[str]:
        """Canonicalize a list of tag IDs against the known vocabulary.

        Args:
            tag_ids: Raw tag IDs to resolve.
            strict: If True, unmatched IDs are dropped; if False, they are
                returned unchanged.

        Returns:
            List of resolved canonical tag IDs.
        """
        resolved_ids = _canonicalise_ids(
            tag_ids,
            self._tag_ids_list,
            strict,
            cutoff=self._match_threshold,
            near_tie_epsilon=self._near_tie_epsilon,
        )
        return [r.resolved_id for r in resolved_ids]

    def canonicalise_tag(self, tag_id: str, strict: bool = False) -> str | None:
        """Canonicalize a single tag ID to its resolved canonical form.

        Args:
            tag_id: The tag ID to be canonicalized.
            strict: If True, applies strict validation rules during canonicalization.
                Defaults to False.

        Returns:
            The resolved canonical form of the given tag ID.
        """
        resolved = self.canonicalise_tags([tag_id], strict=strict)

        resolved_id = resolved[0] if resolved else None

        if resolved_id is not None and not resolved_id.strip():
            resolved_id = None

        if resolved_id is None:
            LOGGER.warning(
                "Tag %r not found in vocabulary",
                tag_id,
                extra={"original_id": tag_id},
            )
        elif LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Resolved Sachgebiet %r → %r",
                tag_id,
                resolved_id,
                extra={"original_id": tag_id, "canonical_id": resolved_id},
            )
        return resolved_id

    def explain(self, query: str, k: int = 5) -> dict[str, Any]:
        """Trace the resolution path of a tag ID query for diagnostics.

        Walks the same steps as :meth:`fuzzy_check_tag` but returns the full
        trace (processed query, exact-match status, top-K candidates,
        configured threshold) instead of a single boolean. Intended for
        debugging and audit output; the returned dict shape is informational
        and may evolve.

        Args:
            query: Raw tag ID string.
            k: Maximum number of fuzzy candidates to include in ``top_k``.

        Returns:
            Dict with keys ``query``, ``processed_query``, ``exact_hit``,
            ``threshold``, ``near_tie_epsilon``, and ``top_k`` (a list of
            ``{id, score}`` dicts ordered by descending score).
        """
        processed_query = _processor_ids(query)
        trace: dict[str, Any] = {
            "query": query,
            "processed_query": processed_query,
            "exact_hit": False,
            "threshold": self._match_threshold,
            "near_tie_epsilon": self._near_tie_epsilon,
            "top_k": [],
        }

        if not processed_query:
            return trace

        if query in self._tag_ids:
            trace["exact_hit"] = True
            trace["top_k"] = [{"id": query, "score": _EXACT_MATCH_THRESHOLD}]
            return trace

        if not self._tag_ids_list:
            return trace

        top_n = min(k, len(self._tag_ids_list))
        candidates = process.extract(
            query,
            self._tag_ids_list,
            scorer=fuzz.token_sort_ratio,
            processor=_processor_ids,
            limit=top_n,
        )
        trace["top_k"] = [
            {"id": match, "score": score} for match, score, _ in candidates
        ]
        return trace

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
            sachgebiet_ids,
            self._sachgebiete_ids_list,
            True,
            cutoff=self._match_threshold,
            near_tie_epsilon=self._near_tie_epsilon,
        )

        return [r.resolved_id for r in resolved_ids]

    def canonicalise_sachgebiet(self, sachgebiet_id: str) -> str | None:
        """Canonicalize a single Sachgebiet identifier.

        Resolves a single sachgebiet ID to its canonical form via
        `canonicalise_sachgebiete`. Returns None if no match is found
        or if the resolved value is blank.

        Args:
            sachgebiet_id: The sachgebiet identifier to canonicalize.

        Returns:
            The canonical sachgebiet identifier, or None if unresolved
            or blank.
        """
        resolved = self.canonicalise_sachgebiete([sachgebiet_id])
        resolved_id = resolved[0] if resolved else None
        if resolved_id is not None and not resolved_id.strip():
            resolved_id = None

        if resolved_id is None:
            LOGGER.warning(
                "Sachgebiet %r not found in vocabulary",
                sachgebiet_id,
                extra={"original_id": sachgebiet_id},
            )
        elif LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Resolved Sachgebiet %r → %r",
                sachgebiet_id,
                resolved_id,
                extra={"original_id": sachgebiet_id, "canonical_id": resolved_id},
            )
        return resolved_id
