"""Validation tool for author mapping YAML files.

Checks a candidate YAML file for conflicts with the existing author
vocabulary before it is merged into the global mappings.

Usage::

    poetry run python -m tools.yaml_validator_authors test_authors.yaml
    poetry run python -m tools.yaml_validator_authors test_authors.yaml \
        extra1.yaml extra2.yaml
    poetry run python -m tools.yaml_validator_authors test_authors.yaml \
        --match-threshold 85
"""

import argparse
import sys
from pathlib import Path

from pazufa_corelib.names_model import Author, AuthorFile
from pazufa_corelib.normalization.names import (
    _FUZZY_MATCH_THRESHOLD,
    AuthorResolver,
)


def yaml_validator_authors(
    yaml_testfile: Path,
    extra_files: list[Path] | None = None,
    match_threshold: float = _FUZZY_MATCH_THRESHOLD,
) -> None:
    """Validate a candidate author YAML file against the existing vocabulary.

    Runs three checks for every entry in *yaml_testfile*:

    1. **ID collision** — the entry's ``id`` must not already exist in the
       global vocabulary.
    2. **Canonical name collision** — the normalized ``canonical_name`` must
       not match an existing entry's canonical name or alias exactly.
    3. **Fuzzy collision** — the ``canonical_name`` must not fuzzy-match an
       existing entry above *match_threshold*, which would cause the resolver
       to confuse real data with an existing author. Only checked when
       checks 1 and 2 pass for the entry.

    Additionally, all entries in *yaml_testfile* are checked against each
    other for fuzzy collisions.

    Checks 1 and 2 are hard errors that raise ``ValueError``. Check 3 produces
    a warning; the caller decides whether the similarity is acceptable.

    If *yaml_testfile* appears in *extra_files* it is removed automatically to
    prevent the new entries from matching against themselves.

    Args:
        yaml_testfile: Path to the YAML file to validate. Must follow the
            ``AuthorFile`` schema (``names:`` list with ``id``,
            ``canonical_name``, optional ``aliases``).
        extra_files: Additional YAML files passed to ``AuthorResolver``
            on top of the global mappings. Useful when the new file depends on
            entries not yet in the global vocabulary.
        match_threshold: Fuzzy similarity threshold (0–100) forwarded to
            ``AuthorResolver``. Defaults to the module-level constant.

    Raises:
        FileNotFoundError: If *yaml_testfile* does not exist.
        ValueError: If *yaml_testfile* fails schema validation, or if any
            entry has an ID or canonical name that collides with an existing
            entry.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Copy to avoid mutating the caller's list; remove yaml_testfile if present
    if extra_files and yaml_testfile in extra_files:
        print(
            f"  ! '{yaml_testfile}' removed from extra_files to prevent false positives"
        )
    extra_files = [f for f in (extra_files or []) if f != yaml_testfile]

    author_resolver = AuthorResolver(
        extra_files=extra_files if extra_files else None,
        match_threshold=match_threshold,
    )
    print("AuthorResolver initialized")

    # Validate YAML structure and types — raises on malformed input
    test_authors: list[Author] = AuthorFile.from_path(yaml_testfile).names
    print(f"Yaml file {yaml_testfile} is valid ({len(test_authors)} entries)")

    for author in test_authors:
        entry_has_error = False

        # --- check 1a: ID collision with existing vocabulary ---
        existing = author_resolver.get_author_by_id(author.id)
        if existing is not None:
            errors.append(
                f"ID '{author.id}' already exists "
                f"(existing canonical: '{existing.canonical_name}')"
            )
            entry_has_error = True

        # --- check 1b: canonical_name exact collision ---
        if author_resolver.check_author(author.canonical_name):
            errors.append(
                f"canonical_name '{author.canonical_name}' "
                "collides with an existing entry"
            )
            entry_has_error = True

        # --- check 2: fuzzy collision against existing vocabulary ---
        # Only run when checks 1a/1b passed to avoid noise on top of hard errors
        if not entry_has_error:
            resolution = author_resolver.resolve(author.canonical_name)
            if resolution.matched:
                warnings.append(
                    f"'{author.canonical_name}' fuzzy-matches existing "
                    f"'{resolution.canonical_name}' (id: '{resolution.resolved_id}', "
                    f"score: {resolution.score:.1f}) — "
                    "too similar to an existing entry; make the name more distinct "
                    "or add it as an alias to the existing entry instead"
                )

    # --- check 3: intra-file fuzzy collisions ---
    # Build a resolver from only the new entries and check each against the rest
    if len(test_authors) > 1:
        intra_resolver = AuthorResolver(
            extra_files=[yaml_testfile],
            match_threshold=match_threshold,
        )
        canonical_names = [author.canonical_name for author in test_authors]
        resolutions = intra_resolver.resolve_batch(canonical_names)
        for author, resolution in zip(test_authors, resolutions):
            different = resolution.canonical_name != author.canonical_name
            if resolution.matched and different:
                warnings.append(
                    f"'{author.canonical_name}' fuzzy-matches another new entry "
                    f"'{resolution.canonical_name}' (score: {resolution.score:.1f}) — "
                    "the two entries may be confused with each other by the resolver"
                )

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
        description="Validate an author YAML file against the vocabulary."
    )
    parser.add_argument("yaml_testfile", type=Path, help="YAML file to validate")
    parser.add_argument(
        "extra_files",
        type=Path,
        nargs="*",
        help="Additional YAML files merged into the resolver before validation",
    )
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=_FUZZY_MATCH_THRESHOLD,
        metavar="SCORE",
        help=f"Fuzzy similarity threshold (0–100, default: {_FUZZY_MATCH_THRESHOLD})",
    )

    args = parser.parse_args()

    try:
        yaml_validator_authors(
            args.yaml_testfile,
            extra_files=args.extra_files or None,
            match_threshold=args.match_threshold,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
