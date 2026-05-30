"""Organization name normalization and resolution."""

import logging
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np

from pazufa_corelib.names_model import (
    Organization,
    OrganizationFile,
    OrganizationIDResolution,
)
from pazufa_corelib.normalization._fuzzy import _EXACT_MATCH_THRESHOLD
from pazufa_corelib.normalization.text import normalize_name

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

ORGANIZATIONS_FILES: tuple[Path, ...] = (
    MAPPINGS_DIR / "parteien.yaml",
    MAPPINGS_DIR / "organizations.yaml",
)
"""Canonical list of paths to the global organization files."""

_NGRAM_SIZE: int = 3
# Cosine scores are scaled to 0–100 to share the scale used by the
# rapidfuzz-based AuthorResolver, so callers can apply a single threshold
# across both resolvers.
_COSINE_MATCH_THRESHOLD: float = 80.0
_COSINE_NEAR_TIE_EPSILON: float = 2.0

LOGGER = logging.getLogger(__name__)


# =====================================================================
# N-gram helpers
# =====================================================================


def _ngrams(text: str, n: int = _NGRAM_SIZE) -> list[str]:
    """Return padded character n-grams for *text*.

    Pads with a single space on each side so short tokens still produce
    edge n-grams (e.g. ``"FDP"`` → ``" FD"``, ``"FDP"``, ``"DP "``).

    Args:
        text: Input string to decompose into n-grams.
        n: N-gram size.

    Returns:
        List of n-gram strings extracted from the padded text.
    """
    padded = f" {text} "
    return [padded[i : i + n] for i in range(len(padded) - n + 1)]


def _build_vocab(keys: list[str], n: int = _NGRAM_SIZE) -> dict[str, int]:
    """Build a trigram vocabulary from a list of normalized keys.

    Args:
        keys: Pre-normalized name strings.
        n: N-gram size.

    Returns:
        Mapping of n-gram string to column index.
    """
    vocab: dict[str, int] = {}
    for key in keys:
        for gram in _ngrams(key, n):
            if gram not in vocab:
                vocab[gram] = len(vocab)
    return vocab


def _vectorize(key: str, vocab: dict[str, int], n: int = _NGRAM_SIZE) -> np.ndarray:
    """Vectorize a normalized key into an L2-normalized n-gram count vector.

    N-grams not present in *vocab* are silently ignored, so the function
    is safe to call on query strings that contain unseen n-grams.

    Args:
        key: Pre-normalized name string.
        vocab: N-gram vocabulary produced by :func:`_build_vocab`.
        n: N-gram size, must match the size used to build *vocab*.

    Returns:
        Float32 array of shape ``(len(vocab),)``, L2-normalized. Returns
        a zero vector if *key* produces no known n-grams.
    """
    vec = np.zeros(len(vocab), dtype=np.float32)
    for gram in _ngrams(key, n):
        if gram in vocab:
            vec[vocab[gram]] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0.0:
        vec /= norm
    return vec


def _build_matrix(
    keys: list[str], vocab: dict[str, int], n: int = _NGRAM_SIZE
) -> np.ndarray:
    """Build an L2-normalized n-gram matrix for a list of keys.

    Args:
        keys: Pre-normalized name strings (one row per key).
        vocab: N-gram vocabulary produced by :func:`_build_vocab`.
        n: N-gram size.

    Returns:
        Float32 array of shape ``(len(keys), len(vocab))`` with each row
        L2-normalized. Cosine similarity between any query vector and
        this matrix is then a plain dot product.
    """
    return np.vstack([_vectorize(k, vocab, n) for k in keys])


# =====================================================================
# Organization loader
# =====================================================================


def _load_organizations(
    files: list[Path] | tuple[Path, ...] = ORGANIZATIONS_FILES,
) -> list[Organization]:
    """Load and merge organizations from the global file and any extra files.

    Files are merged in order; later entries override earlier ones on
    ID collision.

    Args:
        files: YAML files to load. Files are merged in order; later entries
            override earlier ones on ID collision.

    Returns:
        Deduplicated list of :class:`~pazufa_corelib.names_model.Organization`
        objects keyed by ``id``.
    """
    org_map: dict[str, Organization] = {}
    for path in files:
        for org in OrganizationFile.from_path(path).names:
            org_map[org.id] = org
    return list(org_map.values())


# =====================================================================
# File Configuration helpers
# =====================================================================


def default_organization_files() -> dict[str, Path]:
    """Generate a dict of default organization filenames and their file paths.

    This function iterates through a collection of organization-related files
    and creates a mapping where the keys are the stem of each file (the
    filename without its extension) and the values are the full file paths.

    Returns:
        dict[str, Path]: A dictionary where keys are file stems and values
        are corresponding file paths.
    """
    return {p.stem: p for p in ORGANIZATIONS_FILES}


# =====================================================================
# OrganizationResolver
# =====================================================================


class OrganizationResolver:
    """Resolves raw organization name strings to canonical organization IDs.

    Uses character n-gram cosine similarity for matching, which is robust
    to word-order variants and long compound names. Supports both
    single-query and batch resolution.

    Args:
        files: Optional additional organization YAML files merged on
            top of the global mapping. Later files override earlier entries
            on ID collision.
        match_threshold: Minimum cosine score (0–100 scale) a fuzzy match
            must clear to be returned as resolved. Below this, queries are
            reported unresolved. Defaults to the module-level constant.
        near_tie_epsilon: Maximum cosine-score gap (0–100 scale) between
            the best and second-best fuzzy match that triggers a near-tie
            warning log. Defaults to the module-level constant.
    """

    def __init__(
        self,
        files: list[Path] | tuple[Path, ...] = ORGANIZATIONS_FILES,
        match_threshold: float = _COSINE_MATCH_THRESHOLD,
        near_tie_epsilon: float = _COSINE_NEAR_TIE_EPSILON,
    ) -> None:
        if not files:
            raise ValueError("No vocabulary files specified for OrganizationResolver")

        # Attribut declaration from parameters
        self._organizations: list[Organization] = _load_organizations(files)
        self._match_threshold: float = match_threshold
        self._near_tie_epsilon: float = near_tie_epsilon

        # normalized key → (id, canonical_name, acronym)
        self._key_to_org: dict[str, tuple[str, str, str | None]] = {}
        # canonical id → full Organization record
        self._id_to_org: dict[str, Organization] = {}
        for org in self._organizations:
            self._id_to_org[org.id] = org
            for surface in [org.canonical_name, *org.aliases]:
                key = normalize_name(surface)
                if key:
                    self._key_to_org[key] = (org.id, org.canonical_name, org.acronym)

        self._acronym_to_orgs: dict[str, list[Organization]] = {}
        for org in self._organizations:
            if org.acronym is not None:
                self._acronym_to_orgs.setdefault(org.acronym, []).append(org)
        self._canonical_keys: list[str] = list(self._key_to_org)

        # pre-build n-gram index
        self._vocab: dict[str, int] = _build_vocab(self._canonical_keys)
        self._matrix: np.ndarray | None = (
            _build_matrix(self._canonical_keys, self._vocab)
            if self._canonical_keys
            else None
        )

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "OrganizationResolver initialised",
                extra={
                    "extra_file_count": len(files) if files else 0,
                    "organization_count": len(self._organizations),
                    "canonical_key_count": len(self._canonical_keys),
                    "vocab_size": len(self._vocab),
                    "matrix_shape": (
                        self._matrix.shape if self._matrix is not None else None
                    ),
                    "matrix_dtype": (
                        self._matrix.dtype.name if self._matrix is not None else None
                    ),
                    "matrix_bytes": (
                        self._matrix.nbytes if self._matrix is not None else 0
                    ),
                    "key_to_org_bytes": sys.getsizeof(self._key_to_org),
                    "vocab_bytes": sys.getsizeof(self._vocab),
                    "acronym_to_orgs_bytes": sys.getsizeof(self._acronym_to_orgs),
                },
            )

    # =====================================================================
    # Organization actions
    # =====================================================================

    def check_organization(self, query: str) -> bool:
        """Check if a query exactly matches a known organization name or alias.

        Args:
            query: Raw organization name string to check.

        Returns:
            ``True`` if the normalized query matches a known canonical
            organization name or any registered alias.
        """
        return normalize_name(query) in self._key_to_org

    def get_organization_by_id(self, org_id: str) -> Organization | None:
        """Look up the full Organization record by its canonical ID.

        Args:
            org_id: Canonical organization ID as stored in the YAML.

        Returns:
            The matching :class:`~pazufa_corelib.names_model.Organization`,
            or ``None`` if no organization carries this ID.
        """
        return self._id_to_org.get(org_id)

    def get_organizations_by_acronym(self, acronym: str) -> list[Organization]:
        """Return all organizations that carry the given acronym.

        The lookup is case-sensitive and matches the acronym exactly as stored
        in the YAML (e.g. ``"SPD"``, not ``"spd"``).

        Args:
            acronym: Abbreviation to look up, e.g. ``"CDU"``.

        Returns:
            List of matching :class:`~pazufa_corelib.names_model.Organization`
            objects. Empty list if no organization carries this acronym.
        """
        return list(self._acronym_to_orgs.get(acronym, []))

    def fuzzy_check_organization(self, query: str) -> bool:
        """Fuzzy-match a name string against the known organization vocabulary.

        Uses n-gram cosine similarity via :meth:`resolve`.

        Args:
            query: Raw organization name string to check.

        Returns:
            ``True`` if the name matched a known organization above the cosine
            threshold, ``False`` otherwise.
        """
        result = self.resolve(query)
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Fuzzy organization check for %r",
                query,
                extra={
                    "query": query,
                    "matched": result.matched,
                    "score": result.score,
                },
            )
        return result.matched

    def fuzzy_match_acronym(self, query: str) -> str:
        """Resolve a raw organization name to its acronym via fuzzy matching.

        Args:
            query: Raw organization name string.

        Returns:
            The acronym if the query resolves to an organization that has one,
            or the original query otherwise.
        """
        resolved = self.resolve(query)

        if resolved.matched:
            if resolved.acronym is not None:
                if LOGGER.isEnabledFor(logging.DEBUG):
                    LOGGER.debug(
                        "Fuzzy match %r has acronym %r, returning acronym",
                        query,
                        resolved.acronym,
                        extra={
                            "query": query,
                            "matched": resolved.matched,
                            "score": resolved.score,
                        },
                    )
                return resolved.acronym
            else:
                LOGGER.warning(
                    "Fuzzy match %r has no acronym, returning query",
                    query,
                    extra={
                        "query": query,
                        "matched": resolved.matched,
                        "score": resolved.score,
                    },
                )
                return query
        else:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    "Fuzzy organization match %r unresolved, returning query",
                    query,
                    extra={
                        "query": query,
                        "matched": resolved.matched,
                        "score": resolved.score,
                    },
                )
            return query

    def canonicalize_organizations(
        self, queries: list[str], strict: bool = False
    ) -> list[str]:
        """Canonicalize a list of raw organization name strings to canonical names.

        Args:
            queries: Raw organization name strings to resolve.
            strict: If ``True``, unmatched names are dropped from the
                result. If ``False``, the original raw query is kept in
                place for each unmatched name.

        Returns:
            List of resolved canonical organization names, in the same
            order as *queries* (unless ``strict=True`` drops some).
        """
        resolved = self.resolve_batch(queries)

        if strict:
            matched = [r for r in resolved if r.matched]
            dropped = len(resolved) - len(matched)
            if dropped:
                LOGGER.warning(
                    "Dropped %d unresolved organization names (strict=True)",
                    dropped,
                    extra={
                        "strict": True,
                        "query_count": len(queries),
                        "dropped": dropped,
                    },
                )
            return [r.canonical_name for r in matched]
        return [r.canonical_name for r in resolved]

    def canonicalize_organization(self, query: str, strict: bool = False) -> str | None:
        """Canonicalize the given organization name to its standard form.

        Attempts to resolve to a canonical name. Returns None if unresolved
        and strict mode is enabled, otherwise returns the canonical name or
        the original name.

        Args:
            query (str): The name of the organization to be resolved.
            strict (bool, optional): If True, unresolved organizations will be
                dropped and None will be returned. Defaults to False.

        Returns:
            str | None: The canonical name of the organization if resolved. If the
            organization is unresolved and strict is True, returns None. Otherwise,
            returns the original name.
        """
        resolved = self.resolve(query)

        if resolved.matched:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    "Resolved organization %r → %r",
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
                "Dropping unresolved organization %r (strict=True)",
                query,
                extra={"original_name": query, "strict": True},
            )
            return None

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Organization %r unresolved, keeping original",
                query,
                extra={"original_name": query, "strict": False},
            )
        return query

    def resolve(self, query: str) -> OrganizationIDResolution:
        """Resolve a single raw organization name to a canonical entry.

        Resolution order:

        1. Normalize the query with :func:`normalize_name`.
        2. Exact lookup in the normalized-key index.
        3. N-gram cosine similarity against the canonical matrix.
        4. Return unresolved (score ``0.0``) if nothing clears the
           configured ``match_threshold``.

        Args:
            query: Raw organization name string.

        Returns:
            :class:`~pazufa_corelib.names_model.organizationIDResolution`
            with the best match found, or an unresolved result when no
            match cleared the threshold.
        """
        return self.resolve_batch([query])[0]

    def resolve_batch(self, queries: list[str]) -> list[OrganizationIDResolution]:
        """Resolve a batch of raw organization names in a single matmul.

        Args:
            queries: Raw organization name strings.

        Returns:
            List of :class:`~pazufa_corelib.names_model.OrganizationIDResolution`
            in the same order as *queries*.
        """
        if not queries:
            return []

        results: list[OrganizationIDResolution | None] = [None] * len(queries)
        fuzzy_idxs: list[int] = []
        fuzzy_keys: list[str] = []

        # --- first pass: resolve empty queries and exact matches -----------
        for i, query in enumerate(queries):
            query_key = normalize_name(query)

            if not query_key:
                results[i] = OrganizationIDResolution(
                    original_name=query,
                    resolved_id="",
                    canonical_name=query,
                    score=0.0,
                )
                continue

            if query_key in self._key_to_org:
                org_id, canonical_name, acronym = self._key_to_org[query_key]
                results[i] = OrganizationIDResolution(
                    original_name=query,
                    resolved_id=org_id,
                    canonical_name=canonical_name,
                    acronym=acronym,
                    score=_EXACT_MATCH_THRESHOLD,
                )
                continue

            if self._matrix is None:
                results[i] = OrganizationIDResolution(
                    original_name=query,
                    resolved_id="",
                    canonical_name=query,
                    score=0.0,
                )
                continue

            fuzzy_idxs.append(i)
            fuzzy_keys.append(query_key)

        # --- second pass: single matmul for all remaining fuzzy queries ----
        if fuzzy_idxs:
            # guaranteed non-None: fuzzy_idxs only populated when matrix exists
            matrix = cast(np.ndarray, self._matrix)
            q_matrix = _build_matrix(fuzzy_keys, self._vocab)
            # (n_fuzzy, n_canonical)
            scores_matrix = (q_matrix @ matrix.T) * 100.0

            for j, i in enumerate(fuzzy_idxs):
                query = queries[i]
                scores = scores_matrix[j]
                best_idx = int(scores.argmax())
                best_score = float(scores[best_idx])

                if best_score < self._match_threshold:
                    results[i] = OrganizationIDResolution(
                        original_name=query,
                        resolved_id="",
                        canonical_name=query,
                        score=0.0,
                    )
                    continue

                # near-tie warning
                sorted_scores = np.sort(scores)[::-1]
                if len(sorted_scores) >= 2:
                    second_score = float(sorted_scores[1])
                    if (
                        second_score > 0
                        and best_score - second_score <= self._near_tie_epsilon
                    ):
                        second_idx = int(np.where(scores == second_score)[0][0])
                        LOGGER.warning(
                            "Near-tie for organization %r",
                            query,
                            extra={
                                "query": query,
                                "best_match": self._canonical_keys[best_idx],
                                "best_score": best_score,
                                "second_match": self._canonical_keys[second_idx],
                                "second_score": second_score,
                                "delta": best_score - second_score,
                                "epsilon": self._near_tie_epsilon,
                            },
                        )

                org_id, canonical_name, acronym = self._key_to_org[
                    self._canonical_keys[best_idx]
                ]
                results[i] = OrganizationIDResolution(
                    original_name=query,
                    resolved_id=org_id,
                    canonical_name=canonical_name,
                    acronym=acronym,
                    score=best_score,
                )

        return results  # type: ignore[return-value]  # all slots filled by construction

    def explain(self, query: str, k: int = 5) -> dict[str, Any]:
        """Trace the resolution path of a query for diagnostics.

        Walks the same steps as :meth:`resolve` but returns the full trace
        (normalized key, exact-match status, top-K fuzzy candidates,
        configured thresholds) instead of a single resolution. Intended
        for debugging and audit output; the returned dict shape is
        informational and may evolve.

        Args:
            query: Raw organization name string.
            k: Maximum number of fuzzy candidates to include in ``top_k``.

        Returns:
            Dict with keys ``query``, ``normalized_key``, ``exact_hit``,
            ``threshold``, ``near_tie_epsilon``, and ``top_k`` (a list of
            ``{canonical_name, id, acronym, score}`` dicts ordered by
            descending score).
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

        if normalized_key in self._key_to_org:
            org_id, canonical_name, acronym = self._key_to_org[normalized_key]
            trace["exact_hit"] = True
            trace["top_k"] = [
                {
                    "canonical_name": canonical_name,
                    "id": org_id,
                    "acronym": acronym,
                    "score": _EXACT_MATCH_THRESHOLD,
                }
            ]
            return trace

        if self._matrix is None:
            return trace

        q_vec = _build_matrix([normalized_key], self._vocab)
        scores = ((q_vec @ self._matrix.T) * 100.0)[0]
        top_n = min(k, len(self._canonical_keys))
        top_idx = np.argsort(scores, kind="stable")[::-1][:top_n]
        top_k: list[dict[str, Any]] = []
        for raw_i in top_idx:
            i = int(raw_i)
            org_id, canonical_name, acronym = self._key_to_org[self._canonical_keys[i]]
            top_k.append(
                {
                    "canonical_name": canonical_name,
                    "id": org_id,
                    "acronym": acronym,
                    "score": float(scores[i]),
                }
            )
        trace["top_k"] = top_k
        return trace
