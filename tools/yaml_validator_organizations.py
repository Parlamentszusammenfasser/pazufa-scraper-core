"""Validation tool for organization mapping YAML files.

Checks a candidate YAML file for conflicts with the existing organization
vocabulary before it is merged into the global mappings.

Usage::

    poetry run python -m tools.yaml_validator_organizations test_orgs.yaml
    poetry run python -m tools.yaml_validator_organizations test_orgs.yaml \
        extra1.yaml extra2.yaml
    poetry run python -m tools.yaml_validator_organizations test_orgs.yaml \
        --match-threshold 85 --near-tie-epsilon 1.0
"""

import argparse
import sys
from pathlib import Path

from pazufa_corelib.names_model import Organization, OrganizationFile
from pazufa_corelib.normalization.names import (
    _COSINE_MATCH_THRESHOLD,
    _COSINE_NEAR_TIE_EPSILON,
    ORGANIZATIONS_FILES,
    OrganizationResolver,
)


def yaml_validator_organizations(
    yaml_testfile: Path,
    files: list[Path] | None = None,
    match_threshold: float = _COSINE_MATCH_THRESHOLD,
    near_tie_epsilon: float = _COSINE_NEAR_TIE_EPSILON,
) -> None:
    """Validate a candidate organization YAML file against the existing vocabulary.

    Runs three checks for every entry in *yaml_testfile*:

    1. **ID collision** — the entry's ``id`` must not already exist in the
       global vocabulary.
    2. **Canonical name collision** — the normalized ``canonical_name`` must
       not match an existing entry's canonical name exactly.
    3. **Cosine collision** — the ``canonical_name`` must not fuzzy-match an
       existing entry above *match_threshold*, which would cause the resolver
       to confuse real data with an existing organization. Only checked when
       checks 1 and 2 pass for the entry.

    Additionally, all entries in *yaml_testfile* are checked against each
    other for cosine collisions.

    Checks 1 and 2 are hard errors that raise ``ValueError``. Check 3 produces
    a warning; the caller decides whether the similarity is acceptable.

    If *yaml_testfile* appears in *files* it is removed automatically to
    prevent the new entries from matching against themselves.

    The candidate is checked against whatever YAML files you pass via *files*.
    When *files* is ``None``, the built-in ``ORGANIZATIONS_FILES`` are used.
    When *files* is provided it **replaces** the defaults — pass any built-in
    files you still want to check against explicitly alongside your extras.

    Args:
        yaml_testfile: Path to the YAML file to validate. Must follow the
            ``OrganizationFile`` schema (``names:`` list with ``id``,
            ``canonical_name``, optional ``acronym`` and ``aliases``).
        files: Full set of reference YAML files for ``OrganizationResolver``.
            When omitted, defaults to the global ``ORGANIZATIONS_FILES``. When
            provided, overrides the defaults entirely.
        match_threshold: Cosine similarity threshold (0–100) forwarded to
            ``OrganizationResolver``. Defaults to the module-level constant.
        near_tie_epsilon: Near-tie epsilon forwarded to ``OrganizationResolver``.
            Defaults to the module-level constant.

    Raises:
        FileNotFoundError: If *yaml_testfile* does not exist.
        ValueError: If *yaml_testfile* fails schema validation, or if any
            entry has an ID or canonical name that collides with an existing
            entry.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if files is None:
        warnings.append(
            f"No reference files passed; using default ORGANIZATIONS_FILES "
            f"({len(ORGANIZATIONS_FILES)} file(s))."
        )
        files = list(ORGANIZATIONS_FILES)
    else:
        warnings.append(
            "Custom 'files' provided; the default ORGANIZATIONS_FILES are NOT used. "
            "Pass any built-in files you still want to validate against explicitly."
        )
        # Copy to avoid mutating the caller's list; drop yaml_testfile if present
        if yaml_testfile in files:
            print(
                f"  ! '{yaml_testfile}' removed from files to prevent false positives"
            )
        files = [f for f in files if f != yaml_testfile]
        if not files:
            warnings.append(
                "All provided files were filtered out; falling back to default "
                "ORGANIZATIONS_FILES."
            )
            files = list(ORGANIZATIONS_FILES)

    org_resolver = OrganizationResolver(
        files=files,
        match_threshold=match_threshold,
        near_tie_epsilon=near_tie_epsilon,
    )
    print("OrganizationResolver initialized")

    # Validate YAML structure and types — raises on malformed input
    test_organisations: list[Organization] = OrganizationFile.from_path(
        yaml_testfile
    ).names
    print(f"Yaml file {yaml_testfile} is valid ({len(test_organisations)} entries)")

    for org in test_organisations:
        entry_has_error = False

        # --- check 1a: ID collision with existing vocabulary ---
        existing = org_resolver.get_organization_by_id(org.id)
        if existing is not None:
            errors.append(
                f"ID '{org.id}' already exists "
                f"(existing canonical: '{existing.canonical_name}')"
            )
            entry_has_error = True

        # --- check 1b: canonical_name exact collision ---
        if org_resolver.check_organization(org.canonical_name):
            errors.append(
                f"canonical_name '{org.canonical_name}' collides with an existing entry"
            )
            entry_has_error = True

        # --- check 2: cosine collision against existing vocabulary ---
        # Only run when checks 1a/1b passed to avoid noise on top of hard errors
        if not entry_has_error:
            resolution = org_resolver.resolve(org.canonical_name)
            if resolution.matched:
                warnings.append(
                    f"'{org.canonical_name}' fuzzy-matches existing "
                    f"'{resolution.canonical_name}' (id: '{resolution.resolved_id}', "
                    f"score: {resolution.score:.1f}) — "
                    "too similar to an existing entry; make the name more distinct "
                    "or add it as an alias to the existing entry instead"
                )

    # --- check 3: intra-file cosine collisions ---
    # Build a resolver from only the new entries and check each against the rest
    if len(test_organisations) > 1:
        intra_resolver = OrganizationResolver(
            files=[yaml_testfile],
            match_threshold=match_threshold,
            near_tie_epsilon=near_tie_epsilon,
        )
        canonical_names = [org.canonical_name for org in test_organisations]
        resolutions = intra_resolver.resolve_batch(canonical_names)
        for org, resolution in zip(test_organisations, resolutions):
            if resolution.matched and resolution.canonical_name != org.canonical_name:
                warnings.append(
                    f"'{org.canonical_name}' fuzzy-matches another new entry "
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
        description="Validate an organization YAML file against the vocabulary."
    )
    parser.add_argument("yaml_testfile", type=Path, help="YAML file to validate")
    parser.add_argument(
        "files",
        type=Path,
        nargs="*",
        help=(
            "Reference YAML files for the resolver. "
            "Replaces the built-in ORGANIZATIONS_FILES when provided."
        ),
    )
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=_COSINE_MATCH_THRESHOLD,
        metavar="SCORE",
        help=f"Cosine similarity threshold (0–100, default: {_COSINE_MATCH_THRESHOLD})",
    )
    parser.add_argument(
        "--near-tie-epsilon",
        type=float,
        default=_COSINE_NEAR_TIE_EPSILON,
        metavar="DELTA",
        help=f"Near-tie warning epsilon (default: {_COSINE_NEAR_TIE_EPSILON})",
    )

    args = parser.parse_args()

    try:
        yaml_validator_organizations(
            args.yaml_testfile,
            files=args.files or None,
            match_threshold=args.match_threshold,
            near_tie_epsilon=args.near_tie_epsilon,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
