"""Validation tool for tag mapping YAML files.

Checks a candidate YAML file for conflicts with the existing tag
vocabulary before it is merged into the global mappings.

Usage::

    poetry run python -m tools.yaml_validator_tags test_tags.yaml
    poetry run python -m tools.yaml_validator_tags test_tags.yaml \
        extra1.yaml extra2.yaml
"""

import argparse
import sys
from pathlib import Path

from pazufa_corelib.normalization.schlagworte import (
    _FUZZY_MATCH_THRESHOLD,
    _NEAR_TIE_EPSILON,
    SchlagwortResolver,
)
from pazufa_corelib.schlagworte_model import Tag, TagFile


def yaml_validator_tags(
    yaml_testfile: Path,
    extra_files: list[Path] | None = None,
    match_threshold: float = _FUZZY_MATCH_THRESHOLD,
    near_tie_epsilon: float = _NEAR_TIE_EPSILON,
) -> None:
    """Validate a candidate tag YAML file against the existing vocabulary.

    Runs three checks for every entry in *yaml_testfile*:

    1. **ID collision** — the entry's ``id`` must not already exist in the
       global vocabulary.
    2. **Fuzzy ID collision** — the ``id`` must not fuzzy-match an existing
       entry's ID above the module-level threshold, which would cause the
       resolver to confuse the new tag with an existing one. Only checked
       when check 1 passes for the entry.
    3. **Intra-file fuzzy collision** — each new tag's ID is checked against
       all other new tag IDs to detect entries that may be confused with each
       other by the resolver.

    Check 1 is a hard error that raises ``ValueError``. Checks 2 and 3
    produce warnings; the caller decides whether the similarity is acceptable.

    If *yaml_testfile* appears in *extra_files* it is removed automatically to
    prevent the new entries from matching against themselves.

    Args:
        yaml_testfile: Path to the YAML file to validate. Must follow the
            ``TagFile`` schema (``tags:`` list with ``id`` and optional
            ``description``).
        extra_files: Additional tag YAML files loaded as local tags into
            ``SchlagwortResolver`` on top of the global mappings. Useful when
            the new file depends on entries not yet in the global vocabulary.
        match_threshold: Fuzzy similarity threshold (0–100) forwarded to
            ``SchlagwortResolver``. Defaults to the module-level constant.
        near_tie_epsilon: Near-tie epsilon forwarded to ``SchlagwortResolver``.
            Defaults to the module-level constant.

    Raises:
        FileNotFoundError: If *yaml_testfile* does not exist.
        ValueError: If *yaml_testfile* fails schema validation, or if any
            entry has an ID that collides with an existing entry.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Copy to avoid mutating the caller's list; remove yaml_testfile if present
    if extra_files and yaml_testfile in extra_files:
        print(
            f"  ! '{yaml_testfile}' removed from extra_files to prevent false positives"
        )
    extra_files = [f for f in (extra_files or []) if f != yaml_testfile]

    tag_resolver = SchlagwortResolver(
        local_tags=extra_files if extra_files else None,
        match_threshold=match_threshold,
        near_tie_epsilon=near_tie_epsilon,
    )
    print("SchlagwortResolver initialized")

    # Validate YAML structure and types — raises on malformed input
    test_tags: list[Tag] = TagFile.from_path(yaml_testfile).tags
    print(f"Yaml file {yaml_testfile} is valid ({len(test_tags)} entries)")

    for tag in test_tags:
        entry_has_error = False

        # --- check 1: exact ID collision with existing vocabulary ---
        if tag_resolver.check_tag(tag.id):
            errors.append(f"ID '{tag.id}' already exists in the vocabulary")
            entry_has_error = True

        # --- check 2: fuzzy ID collision against existing vocabulary ---
        # Only run when check 1 passed to avoid noise on top of hard errors
        if not entry_has_error:
            trace = tag_resolver.explain(tag.id)
            for candidate in trace["top_k"]:
                if (
                    candidate["id"] != tag.id
                    and candidate["score"] >= _FUZZY_MATCH_THRESHOLD
                ):
                    warnings.append(
                        f"'{tag.id}' fuzzy-matches existing "
                        f"'{candidate['id']}' (score: {candidate['score']:.1f}) — "
                        "too similar to an existing entry; make the ID more distinct "
                        "or add the new tag as a variant of the existing one instead"
                    )
                    break  # report only the strongest match

    # --- check 3: intra-file fuzzy collisions ---
    # Load the new entries into a resolver and check each against the rest
    if len(test_tags) > 1:
        intra_resolver = SchlagwortResolver(local_tags=[yaml_testfile], match_threshold=match_threshold, near_tie_epsilon=near_tie_epsilon)
        new_ids = {tag.id for tag in test_tags}
        reported: set[frozenset[str]] = set()
        for tag in test_tags:
            trace = intra_resolver.explain(tag.id)
            for candidate in trace["top_k"]:
                pair = frozenset({tag.id, candidate["id"]})
                if (
                    candidate["id"] != tag.id
                    and candidate["id"] in new_ids
                    and candidate["score"] >= _FUZZY_MATCH_THRESHOLD
                    and pair not in reported
                ):
                    reported.add(pair)
                    warnings.append(
                        f"'{tag.id}' fuzzy-matches another new entry "
                        f"'{candidate['id']}' (score: {candidate['score']:.1f}) — "
                        "the two entries may be confused with each other by the resolver"
                    )
                    break

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  x {e}")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ! {w}")
    if not errors and not warnings:
        print("All checks passed.")
    if errors:
        raise ValueError(f"{len(errors)} conflict(s) found in {yaml_testfile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate a tag YAML file against the vocabulary."
    )
    parser.add_argument("yaml_testfile", type=Path, help="YAML file to validate")
    parser.add_argument(
        "extra_files",
        type=Path,
        nargs="*",
        help="Additional tag YAML files loaded as local tags before validation",
    )
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=_FUZZY_MATCH_THRESHOLD,
        metavar="SCORE",
        help=f"Fuzzy similarity threshold (0–100, default: {_FUZZY_MATCH_THRESHOLD})",
    )
    parser.add_argument(
        "--near-tie-epsilon",
        type=float,
        default=_NEAR_TIE_EPSILON,
        metavar="DELTA",
        help=f"Near-tie warning epsilon (default: {_NEAR_TIE_EPSILON})",
    )

    args = parser.parse_args()

    try:
        yaml_validator_tags(
            args.yaml_testfile,
            extra_files=args.extra_files or None,
            match_threshold=args.match_threshold,
            near_tie_epsilon=args.near_tie_epsilon,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
