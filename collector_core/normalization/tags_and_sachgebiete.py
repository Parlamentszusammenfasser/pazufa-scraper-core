from pathlib import Path
import json
import yaml
import numpy as np
from pathlib import Path
import logging

from collector_core.tags_and_sachgebiete_model import (
    Tag,
    Sachgebiet,
    TagFile,
    SachgebietFile,
    BaseTagFile,
    BaseTag,
)

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

GLOBAL_TAGS_FILES: list[Path] = [MAPPINGS_DIR.joinpath("global_tags.yaml")]
"""Constant list of the paths to the global tag files."""
SACHGEBIETE_FILES: list[Path] = [MAPPINGS_DIR.joinpath("sachgebiete.yaml")]
"""Constant list of the paths to the sachgebiet files."""

TEMPORARY_FILES_FOLDER_DIR: Path = Path(__file__).parent / "temporary"
"""Path to the directory for the temporary files written in normalization."""

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
    """Return the canonical id if an exact case-insensitive match exists, otherwise return as-is."""
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


# =====================================================================
# Public lifetime functions
# =====================================================================


def generate_tags_npy():
    pass


def generate_sachgebiete_npy():
    pass


# =====================================================================
# Public action functions
# =====================================================================


def get_tags_json():
    pass


def get_tags_npy():
    pass


def get_sachgebiete_json():
    pass


def get_sachgebiete_npy():
    pass


def check_tags():
    # optional give local path to tags.npy for faster checks
    pass
