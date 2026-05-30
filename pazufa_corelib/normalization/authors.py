"""Author name normalization and resolution."""

import logging
import sys
import warnings
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

from pazufa_corelib.api_model import Autor
from pazufa_corelib.names_model import (
    Author,
    AuthorFile,
    AuthorIDResolution,
    OrganizationIDResolution,
)
from pazufa_corelib.normalization._fuzzy import _EXACT_MATCH_THRESHOLD, fuzzy_resolve
from pazufa_corelib.normalization.text import normalize_name

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

AUTHORS_FILES: tuple[Path, ...] = (MAPPINGS_DIR / "authors.yaml",)
"""Canonical list of paths to the global author files."""

_FUZZY_MATCH_THRESHOLD: float = 90.0
_NEAR_TIE_EPSILON: float = 1.0

LOGGER = logging.getLogger(__name__)


# =====================================================================
# Private helpers
# =====================================================================


def _load_authors(files: list[Path] | tuple[Path, ...] = AUTHORS_FILES) -> list[Author]:
    """Loads authors from the specified files and returns a list of unique authors.

    Parses the provided files to retrieve author information, consolidates them into
    unique entries based on their IDs, and returns a list of `Author` objects.

    Args:
        files (list[Path] | tuple[Path, ...], optional): A list or tuple of file
            paths to be parsed for author information. Defaults to
            `AUTHORS_FILES`.

    Returns:
        list[Author]: A list of unique `Author` objects extracted from the
        provided files.
    """
    author_map: dict[str, Author] = {}
    for path in files:
        for author in AuthorFile.from_path(path).names:
            author_map[author.id] = author
    return list(author_map.values())


def _canonicalize_names(
    raw_names: list[str],
    canonical_keys: list[str],
    key_to_author: dict[str, tuple[str, str]],
    cutoff: float = _FUZZY_MATCH_THRESHOLD,
    near_tie_epsilon: float = _NEAR_TIE_EPSILON,
) -> list[AuthorIDResolution]:
    """Canonicalize raw names using fuzzy matching against canonical keys.

    Associates each resolved name with an author ID and canonical name
    from a provided mapping.

    Args:
        raw_names: A list of strings representing the raw names to be resolved.
        canonical_keys: A list of strings representing canonical keys to match against.
        key_to_author: A dictionary mapping canonical keys to a tuple containing
            the associated author ID and canonical name.
        cutoff: A float threshold for fuzzy matching scores, below which matches
            are considered invalid. Defaults to _FUZZY_MATCH_THRESHOLD.
        near_tie_epsilon: Maximum score gap between best and second-best match that
            triggers a near-tie warning. Defaults to _NEAR_TIE_EPSILON.

    Returns:
        A list of AuthorIDResolution objects, each representing the resolution of a
        raw name. This includes the original name, resolved author ID, canonical name,
        and the associated fuzzy matching score.
    """
    pairs = fuzzy_resolve(
        raw_names,
        canonical_keys,
        scorer=fuzz.WRatio,
        processor=None,  # callers pre-normalize; avoid double work
        cutoff=cutoff,
        strict=False,
        near_tie_epsilon=near_tie_epsilon,
    )
    result: list[AuthorIDResolution] = []
    for original, resolved_key, score in pairs:
        if score == 0.0:
            result.append(
                AuthorIDResolution(
                    original_name=original,
                    resolved_id="",
                    canonical_name=original,
                    score=0.0,
                )
            )
        else:
            author_id, canonical_name = key_to_author[resolved_key]
            result.append(
                AuthorIDResolution(
                    original_name=original,
                    resolved_id=author_id,
                    canonical_name=canonical_name,
                    score=score,
                )
            )
    return result


# =====================================================================
# File Configuration helpers
# =====================================================================


def default_author_files() -> dict[str, Path]:
    """Generates a dict of default author filenames and their corresponding file paths.

    This function iterates through a collection of author-related files
    and creates a mapping where the keys are the stem of each file (the
    filename without its extension) and the values are the full file paths.

    Returns:
        dict[str, Path]: A dictionary where keys are file stems and values
        are corresponding file paths.
    """
    return {p.stem: p for p in AUTHORS_FILES}


# =====================================================================
# AuthorResolver
# =====================================================================


class AuthorResolver:
    """Resolve raw author name strings to canonical author IDs.

    Supports exact lookup (normalized key index) and fuzzy matching via
    rapidfuzz WRatio. Both exact and fuzzy matches return the same
    :class:`~pazufa_corelib.names_model.AuthorIDResolution` result type.

    Attributes:
        files (list[Path] | tuple[Path, ...]): List of file paths from which author
            data is loaded, defaulting to ``AUTHORS_FILES``. Later files override
            earlier ones on ID collision.
        match_threshold (float): Minimum fuzzy score a match must reach to be
            returned as resolved.
    """

    def __init__(
        self,
        files: list[Path] | tuple[Path, ...] = AUTHORS_FILES,
        match_threshold: float = _FUZZY_MATCH_THRESHOLD,
        near_tie_epsilon: float = _NEAR_TIE_EPSILON,
    ) -> None:

        if not files:
            raise ValueError("No vocabulary files specified for AuthorResolver")

        self._match_threshold = match_threshold
        self._authors: list[Author] = _load_authors(files)
        self._near_tie_epsilon = near_tie_epsilon

        # normalized key → (id, canonical_name)
        self._key_to_author: dict[str, tuple[str, str]] = {}
        for author in self._authors:
            for surface in [author.canonical_name, *author.aliases]:
                key = normalize_name(surface)
                if key:
                    self._key_to_author[key] = (author.id, author.canonical_name)

        self._canonical_keys: list[str] = list(self._key_to_author)
        self._id_to_author: dict[str, Author] = {a.id: a for a in self._authors}

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "AuthorResolver initialised",
                extra={
                    "extra_file_count": len(files),
                    "author_count": len(self._authors),
                    "canonical_key_count": len(self._canonical_keys),
                    "key_to_author_bytes": sys.getsizeof(self._key_to_author),
                    "canonical_keys_bytes": sys.getsizeof(self._canonical_keys),
                    "id_to_author_bytes": sys.getsizeof(self._id_to_author),
                },
            )

    # =====================================================================
    # Author actions
    # =====================================================================

    def check_author(self, query: str) -> bool:
        """Check whether a query string exactly matches a known author name or alias.

        Args:
            query: Raw name string to check.

        Returns:
            ``True`` if the normalized query matches a known canonical author
            name or any registered alias.
        """
        return normalize_name(query) in self._key_to_author

    def fuzzy_check_author(self, query: str) -> bool:
        """Fuzzy-match a name string against the known author vocabulary.

        Uses :meth:`resolve` to find the best match.

        Args:
            query: Raw name string to check.

        Returns:
            ``True`` if the name matched a known author above the fuzzy
            cutoff, ``False`` otherwise.
        """
        result = self.resolve(query)
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Fuzzy author check for %r",
                query,
                extra={
                    "query": query,
                    "matched": result.matched,
                    "score": result.score,
                },
            )
        return result.matched

    def get_author_by_id(self, author_id: str) -> Author | None:
        """Retrieves an author by their unique identifier.

        This method searches for and retrieves an `Author` object associated with the
        given `author_id`. If no author is found for the provided identifier, the method
        returns `None`.

        Args:
            author_id (str): The unique identifier of the author to retrieve.

        Returns:
            Author | None: The `Author` object if found, or `None` if no author
            matches the provided `author_id`.
        """
        return self._id_to_author.get(author_id)

    def canonicalize_authors(
        self, queries: list[str], strict: bool = False
    ) -> list[str | None]:
        """Canonicalizes a list of author names to their standardized forms.

        This function resolves the provided list of author names into their
        canonical forms. It supports a strict matching mode, where unresolved
        names are explicitly set to None and a warning is logged. Otherwise,
        the function attempts to return the canonical forms for all resolvable
        names without logging unresolved names.

        Args:
            queries (list[str]): A list of author names to be resolved into
                their canonical forms.
            strict (bool, optional): If True, unresolved author names are set
                to None, and a warning is logged. Defaults to False.

        Returns:
            list[str | None]: A list of canonical author names for the input
                queries. If strict is True, unresolved names will appear as None.
                Otherwise, all resolvable names are returned in their canonical
                forms.
        """
        if not queries:
            return []

        resolved = self.resolve_batch(queries)

        if strict:
            result: list[str | None] = [
                r.canonical_name if r.matched else None for r in resolved
            ]
            unresolved: int = sum(1 for r in result if r is None)

            if unresolved > 0:
                LOGGER.warning(
                    "Set %d unresolved author names to None (strict=True)",
                    unresolved,
                    extra={"strict": True, "query_count": len(queries)},
                )
            return result

        return [r.canonical_name for r in resolved]

    def canonicalize_author(self, query: str, strict: bool = False) -> str | None:
        """Resolve and return the canonical name of an author based on the query.

        Attempts to resolve the author's name to a canonical form. Returns the
        canonical name if found. If unresolved, returns None when strict=True,
        otherwise returns the original query.

        Args:
            query (str): The name of the author to resolve.
            strict (bool, optional): If True, returns None for unresolved authors.
                Defaults to False.

        Returns:
            str | None: Canonical name if resolved; None if unresolved and
            strict=True; original query otherwise.
        """
        resolved = self.resolve(query)

        if resolved.matched:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    "Resolved author %r → %r",
                    query,
                    resolved.canonical_name,
                    extra={
                        "original_name": query,
                        "canonical_name": resolved.canonical_name,
                        "score": resolved.score,
                    },
                )
            return resolved.canonical_name

        if strict:
            LOGGER.warning(
                "Dropping unresolved author %r (strict=True)",
                query,
                extra={"original_name": query, "strict": True},
            )
            return None

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Author %r unresolved, keeping original",
                query,
                extra={"original_name": query, "strict": False},
            )
        return query

    def resolve(self, query: str) -> AuthorIDResolution:
        """Resolve a single raw author name to a canonical entry.

        Delegates to :meth:`resolve_batch`. Returns the full
        :class:`AuthorIDResolution` (ID, score, canonical name,
        ``matched``/``changed`` flags). For most callers the higher-level
        :meth:`canonicalize_author` is sufficient; use ``resolve`` when
        the score or ID is needed.

        Args:
            query: Raw author name string.

        Returns:
            :class:`~pazufa_corelib.names_model.AuthorIDResolution` with
            the best match found, or an unresolved result when no match
            cleared the threshold.
        """
        return self.resolve_batch([query])[0]

    def resolve_batch(self, queries: list[str]) -> list[AuthorIDResolution]:
        """Resolve a batch of raw author names in a single fuzzy-match pass.

        More efficient than calling :meth:`resolve` in a loop because all
        fuzzy queries are processed in a single :func:`_canonicalize_names`
        call.

        Resolution order for each query:

        1. Normalize with :func:`normalize_name`.
        2. Exact lookup in the normalized-key index.
        3. Fuzzy match via :func:`_canonicalize_names` (batched across all
           non-exact queries).
        4. Return unresolved (score ``0.0``) if nothing clears the
           configured ``fuzzy_cutoff``.

        Args:
            queries: Raw author name strings.

        Returns:
            List of :class:`~pazufa_corelib.names_model.AuthorIDResolution`
            in the same order as *queries*.
        """
        if not queries:
            return []

        results: list[AuthorIDResolution | None] = [None] * len(queries)
        fuzzy_idxs: list[int] = []
        fuzzy_keys: list[str] = []

        for i, query in enumerate(queries):
            query_key = normalize_name(query)

            if not query_key:
                results[i] = AuthorIDResolution(
                    original_name=query,
                    resolved_id="",
                    canonical_name=query,
                    score=0.0,
                )
                continue

            if query_key in self._key_to_author:
                author_id, canonical_name = self._key_to_author[query_key]
                results[i] = AuthorIDResolution(
                    original_name=query,
                    resolved_id=author_id,
                    canonical_name=canonical_name,
                    score=_EXACT_MATCH_THRESHOLD,
                )
                continue

            fuzzy_idxs.append(i)
            fuzzy_keys.append(query_key)

        if fuzzy_idxs:
            if not self._canonical_keys:
                for i in fuzzy_idxs:
                    results[i] = AuthorIDResolution(
                        original_name=queries[i],
                        resolved_id="",
                        canonical_name=queries[i],
                        score=0.0,
                    )
            else:
                resolved = _canonicalize_names(
                    fuzzy_keys,
                    self._canonical_keys,
                    self._key_to_author,
                    self._match_threshold,
                    self._near_tie_epsilon,
                )
                for j, i in enumerate(fuzzy_idxs):
                    r = resolved[j]
                    if r.matched:
                        results[i] = AuthorIDResolution(
                            original_name=queries[i],
                            resolved_id=r.resolved_id,
                            canonical_name=r.canonical_name,
                            score=r.score,
                        )
                    else:
                        results[i] = AuthorIDResolution(
                            original_name=queries[i],
                            resolved_id="",
                            canonical_name=queries[i],
                            score=0.0,
                        )

        return results  # type: ignore[return-value]  # all slots filled by construction

    def explain(self, query: str, k: int = 5) -> dict[str, Any]:
        """Trace the resolution path of a query for diagnostics.

        Walks the same steps as :meth:`resolve` but returns the full trace
        (normalized key, exact-match status, top-K fuzzy candidates,
        configured threshold) instead of a single resolution. Intended
        for debugging and audit output; the returned dict shape is
        informational and may evolve.

        Args:
            query: Raw author name string.
            k: Maximum number of fuzzy candidates to include in ``top_k``.

        Returns:
            Dict with keys ``query``, ``normalized_key``, ``exact_hit``,
            ``threshold``, ``near_tie_epsilon``, and ``top_k`` (a list of
            ``{canonical_name, id, score}`` dicts ordered by descending score).
        """
        normalized_key = normalize_name(query)
        trace: dict[str, Any] = {
            "query": query,
            "normalized_key": normalized_key,
            "exact_hit": False,
            "threshold": self._match_threshold,
            "near_tie_epsilon": self._near_tie_epsilon,
            "top_k": [],
        }

        if not normalized_key:
            return trace

        if normalized_key in self._key_to_author:
            author_id, canonical_name = self._key_to_author[normalized_key]
            trace["exact_hit"] = True
            trace["top_k"] = [
                {
                    "canonical_name": canonical_name,
                    "id": author_id,
                    "score": _EXACT_MATCH_THRESHOLD,
                }
            ]
            return trace

        if not self._canonical_keys:
            return trace

        top_n = min(k, len(self._canonical_keys))
        candidates = process.extract(  # type: ignore[call-overload]
            normalized_key,
            self._canonical_keys,
            scorer=fuzz.WRatio,
            processor=None,
            limit=top_n,
        )
        top_k: list[dict[str, Any]] = []
        for match, score, _ in candidates:
            author_id, canonical_name = self._key_to_author[match]
            top_k.append(
                {
                    "canonical_name": canonical_name,
                    "id": author_id,
                    "score": score,
                }
            )
        trace["top_k"] = top_k
        return trace


# =====================================================================
# Experimental Functions
# =====================================================================


def normalize_autor(
    item: Autor,
    author_resolver: AuthorResolver,
    organization_resolver: "OrganizationResolver",
) -> None:
    """Normalize the ``organisation`` and ``person`` fields of an Autor in-place.

    Resolves each field against the provided resolvers and updates it to the
    canonical name if a match is found; logs debug information otherwise.

    The original raw values are overwritten and not preserved. Callers that
    need the score, ID, or original string should use the resolvers directly.

    For batches of many ``Autor`` instances, calling this in a loop pays
    per-item matmul cost in :class:`OrganizationResolver`. Prefer
    :meth:`OrganizationResolver.resolve_batch` and write back manually.

    .. warning::
        Experimental — may be removed or changed without notice.

    Args:
        item: The Autor object whose fields are normalized in-place.
        author_resolver: Resolver used to normalize the ``person`` field.
        organization_resolver: Resolver used to normalize the
            ``organisation`` field.

    Raises:
        ValueError: If ``item.organisation`` is empty or whitespace-only.
    """
    warnings.warn(
        "normalize_autor is experimental and may be removed or changed without notice.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not item.organisation.strip():
        raise ValueError("Autor.organisation must be a non-empty string")
    org_resolution: OrganizationIDResolution = organization_resolver.resolve(
        item.organisation
    )
    if org_resolution.score > 0:
        item.organisation = org_resolution.canonical_name
    else:
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "organization not resolvable",
                extra={"raw": item.organisation, "score": org_resolution.score},
            )

    if item.person is None or item.person.strip() == "":
        item.person = None
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("author person empty")
    else:
        # No error risen here, as an empty person is allowed.
        person_resolution = author_resolver.resolve(item.person)
        if person_resolution.score > 0:
            item.person = person_resolution.canonical_name
        else:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    "author not resolvable",
                    extra={"raw": item.person, "score": person_resolution.score},
                )


# Avoid a circular import: OrganizationResolver is only needed at runtime in
# normalize_autor, not at class-definition time.
from pazufa_corelib.normalization.organizations import OrganizationResolver  # noqa: E402
