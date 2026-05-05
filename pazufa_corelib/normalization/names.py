"""Name normalization and resolution for authors and organizations."""

import logging
import re
import sys
from pathlib import Path

import numpy as np
from rapidfuzz import fuzz

from pazufa_corelib.names_model import (
    Author,
    AuthorFile,
    AuthorIDResolution,
    Organization,
    OrganizationFile,
    OrganizationIDResolution,
)
from pazufa_corelib.normalization._fuzzy import fuzzy_resolve
from pazufa_corelib.normalization.text import normalize_name_key

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

AUTHORS_FILES: list[Path] = [MAPPINGS_DIR / "authors.yaml"]
"""Canonical list of paths to the global author files."""

ORGANIZATIONS_FILES: list[Path] = [
    MAPPINGS_DIR / "parteien.yaml",
    MAPPINGS_DIR / "organizations.yaml",
]
"""Canonical list of paths to the global organization files."""

_EXACT_MATCH_THRESHOLD: float = 100.0
_FUZZY_MATCH_THRESHOLD: float = 90.0
_NEAR_TIE_EPSILON: float = 1.0

_NGRAM_SIZE: int = 3
# Cosine scores are scaled to 0–100 to share the scale used by the
# rapidfuzz-based AuthorResolver, so callers can apply a single threshold
# across both resolvers.
_COSINE_MATCH_THRESHOLD: float = 80.0
_COSINE_NEAR_TIE_EPSILON: float = 2.0

LOGGER = logging.getLogger(__name__)

# German academic titles and parliamentary post-nominals.
# Stripped before key derivation so they don't influence matching.
_RE_HONORIFICS = re.compile(
    r"(?<!\w)(?:"
    r"Dr\.(?:-Ing\.|-rer\.nat\.|-phil\.|-jur\.)?"
    r"|Prof\.(?:\s+Dr\.)?"
    r"|Dipl\.-\w+"
    r"|M\.(?:A|Sc|Ed|B)\."
    r"|B\.(?:A|Sc|Ed)\."
    r"|Ph\.D\."
    r"|MdB|MdL|MdEP"
    r"|a\.D\."
    r")(?!\w)",
    re.IGNORECASE,
)


# =====================================================================
# Private helpers
# =====================================================================


def normalize_name(raw: str) -> str:
    """Normalize a person or organization name to a stable comparison key.

    Pipeline:

    1. Strip honorifics and post-nominals (``Dr.``, ``Prof.``, ``MdB``, …)
    2. Apply :func:`normalize_name_key` (NFKC, umlaut fold, lowercase,
       strip punctuation, collapse whitespace)
    3. Token-sort — ``"Maria Müller"`` and ``"Müller, Maria"`` produce the
       same key

    Args:
        raw: Raw name string, e.g., from scraped parliamentary data.

    Returns:
        Lowercase, umlaut-folded, honorific-stripped, token-sorted key.
    """
    text = _RE_HONORIFICS.sub(" ", raw)
    text = normalize_name_key(text)
    tokens = text.split()
    tokens.sort()
    return " ".join(tokens)


def _load_authors(extra_files: list[Path] | None = None) -> list[Author]:
    """Load and merge authors from the global file and any extra files.

    Files are merged in order; later entries override earlier ones on
    ID collision.

    Args:
        extra_files: Optional additional YAML files merged on top of the
            global author mapping.

    Returns:
        Deduplicated list of :class:`~pazufa_corelib.names_model.Author`
        objects keyed by ``id``.
    """
    files = AUTHORS_FILES + (extra_files or [])
    author_map: dict[str, Author] = {}
    for path in files:
        for author in AuthorFile.from_path(path).names:
            author_map[author.id] = author
    return list(author_map.values())


def _canonicalize_names(
    raw_names: list[str],
    canonical_keys: list[str],
    key_to_author: dict[str, tuple[str, str]],
    strict: bool = False,
    cutoff: float = _FUZZY_MATCH_THRESHOLD,
) -> list[AuthorIDResolution]:
    """Fuzzy-match raw name strings against canonical normalized keys.

    Each raw name is matched to its closest canonical key using
    ``WRatio`` scoring. Near-tie matches are logged as warnings.

    Args:
        raw_names: Name strings to resolve.
        canonical_keys: Pre-normalized keys to match against.
        key_to_author: Mapping of normalized key to ``(id, canonical_name)``.
        strict: If ``True``, drop names that fall below the cutoff.
            If ``False``, keep them with score ``0.0``.
        cutoff: Minimum fuzzy-match score; scores below are treated as 0.

    Returns:
        A list of :class:`~pazufa_corelib.names_model.AuthorIDResolution`
        with the original name, resolved ID, canonical name, and match score.

    Raises:
        ValueError: If ``raw_names`` or ``canonical_keys`` is empty.
    """
    pairs = fuzzy_resolve(
        raw_names,
        canonical_keys,
        scorer=fuzz.WRatio,
        processor=None,  # callers pre-normalize; avoid double work
        cutoff=cutoff,
        strict=strict,
        near_tie_epsilon=_NEAR_TIE_EPSILON,
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
# AuthorResolver
# =====================================================================


class AuthorResolver:
    """Resolves raw author name strings to canonical author information.

    Loads the global author YAML and any caller-supplied extra files,
    builds a normalized-key lookup, and resolves queries via exact match
    first, then rapidfuzz ``WRatio`` fuzzy matching.

    Args:
        extra_files: Optional additional author YAML files merged on top
            of the global mapping. Later files override earlier entries
            on ID collision.
        fuzzy_cutoff: Minimum ``WRatio`` score for a fuzzy match to be
            accepted. Scores below this threshold are treated as no match.
            Defaults to :data:`_FUZZY_MATCH_THRESHOLD`.
    """

    def __init__(
        self,
        extra_files: list[Path] | None = None,
        fuzzy_cutoff: float = _FUZZY_MATCH_THRESHOLD,
    ) -> None:
        self._fuzzy_cutoff = fuzzy_cutoff
        self._authors: list[Author] = _load_authors(extra_files)

        # normalized key → (id, canonical_name)
        self._key_to_author: dict[str, tuple[str, str]] = {}
        for author in self._authors:
            for surface in [author.canonical_name, *author.aliases]:
                key = normalize_name(surface)
                if key:
                    self._key_to_author[key] = (author.id, author.canonical_name)

        self._canonical_name_keys: set[str] = {
            k for a in self._authors if (k := normalize_name(a.canonical_name))
        }
        self._canonical_keys: list[str] = list(self._key_to_author)

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "AuthorResolver initialised",
                extra={
                    "extra_file_count": len(extra_files) if extra_files else 0,
                    "author_count": len(self._authors),
                    "canonical_key_count": len(self._canonical_keys),
                    "key_to_author_bytes": sys.getsizeof(self._key_to_author),
                    "canonical_keys_bytes": sys.getsizeof(self._canonical_keys),
                },
            )

    # =====================================================================
    # Author actions
    # =====================================================================

    def check_author(self, query: str) -> bool:
        """Check whether a query string exactly matches a known canonical author name.

        Aliases are not considered; only canonical names are checked.

        Args:
            query: Raw name string to check.

        Returns:
            ``True`` if the normalized query matches a known canonical author name.
        """
        return normalize_name(query) in self._canonical_name_keys

    def fuzzy_check_author(self, query: str) -> bool:
        """Fuzzy-match a name string against the known author vocabulary.

        Uses :func:`_canonicalize_names` to find the best fuzzy match.

        Args:
            query: Raw name string to check.

        Returns:
            ``True`` if the name matched a known author above the fuzzy
            cutoff, ``False`` otherwise.
        """
        result = _canonicalize_names(
            [normalize_name(query)],
            self._canonical_keys,
            self._key_to_author,
            cutoff=self._fuzzy_cutoff,
        )[0]
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

    def canonicalize_authors(
        self, queries: list[str], strict: bool = False
    ) -> list[str]:
        """Canonicalize a list of raw name strings to canonical author names.

        More performant than calling :meth:`canonicalize_author` in a loop
        because the underlying fuzzy match runs as a single batch.

        Args:
            queries: Raw name strings to resolve.
            strict: If ``True``, unmatched names are dropped from the
                result. If ``False``, the normalized form of each unmatched
                query is kept in place (note: this is the *normalized*
                fallback, not the raw query — :meth:`canonicalize_author`
                returns the raw query instead).

        Returns:
            List of resolved canonical author names, in the same order as
            *queries* (unless ``strict=True`` drops some).
        """
        if not queries:
            return []

        output: list[str | None] = [None] * len(queries)
        fuzzy_idxs: list[int] = []
        fuzzy_keys: list[str] = []

        for i, query in enumerate(queries):
            key = normalize_name(query)
            if key in self._key_to_author:
                _, canonical_name = self._key_to_author[key]
                output[i] = canonical_name
            else:
                fuzzy_idxs.append(i)
                fuzzy_keys.append(key)

        if fuzzy_keys:
            resolved = _canonicalize_names(
                fuzzy_keys,
                self._canonical_keys,
                self._key_to_author,
                strict=False,  # handle strict below so we can count dropped
                cutoff=self._fuzzy_cutoff,
            )
            for j, i in enumerate(fuzzy_idxs):
                r = resolved[j]
                if r.matched or not strict:
                    output[i] = r.canonical_name
                # strict + unmatched: output[i] stays None → dropped

        if strict:
            result = [v for v in output if v is not None]
            dropped = output.count(None)
            if dropped:
                LOGGER.warning(
                    "Dropped %d unresolved author names (strict=True)",
                    dropped,
                    extra={"strict": True, "query_count": len(queries)},
                )
            return result
        return output  # type: ignore[return-value]  # all slots filled in non-strict

    def canonicalize_author(self, query: str, strict: bool = False) -> str:
        """Resolve a raw author name to its canonical form.

        Args:
            query: The name of the author to canonicalize.
            strict: If ``True``, unresolved names result in an empty string.
                Defaults to ``False``.

        Returns:
            The canonical name if resolved, the original query if unresolved
            and ``strict=False``, or an empty string if unresolved and
            ``strict=True``.
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
            return ""

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Author %r unresolved, keeping original",
                query,
                extra={"original_name": query, "strict": False},
            )
        return query

    def resolve(self, query: str) -> AuthorIDResolution:
        """Resolve a single raw author name to a canonical entry.

        Returns the full :class:`AuthorIDResolution` (ID, score, canonical
        name, ``matched``/``changed`` flags). For most callers the higher-
        level :meth:`canonicalize_author` is sufficient; use ``resolve``
        when the score or ID is needed.

        Resolution order:

        1. normalize the query with :func:`normalize_name`.
        2. Exact lookup in the normalized-key index.
        3. Fuzzy match via :func:`_canonicalize_names`.
        4. Return unresolved (score ``0.0``) if nothing clears
           ``_FUZZY_MATCH_THRESHOLD``.

        Args:
            query: Raw author name string.

        Returns:
            :class:`~pazufa_corelib.names_model.AuthorIDResolution` with
            the best match found, or an unresolved result when no match
            cleared the threshold.
        """
        query_key = normalize_name(query)

        if not query_key:
            return AuthorIDResolution(
                original_name=query,
                resolved_id="",
                canonical_name=query,
                score=0.0,
            )

        # --- exact match ------------------------------------------------
        if query_key in self._key_to_author:
            author_id, canonical_name = self._key_to_author[query_key]
            return AuthorIDResolution(
                original_name=query,
                resolved_id=author_id,
                canonical_name=canonical_name,
                score=_EXACT_MATCH_THRESHOLD,
            )

        # --- fuzzy match ------------------------------------------------
        if not self._canonical_keys:
            return AuthorIDResolution(
                original_name=query,
                resolved_id="",
                canonical_name=query,
                score=0.0,
            )

        return _canonicalize_names(
            [query_key],
            self._canonical_keys,
            self._key_to_author,
            cutoff=self._fuzzy_cutoff,
        )[0]


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


def _load_organizations(extra_files: list[Path] | None = None) -> list[Organization]:
    """Load and merge organizations from the global file and any extra files.

    Files are merged in order; later entries override earlier ones on
    ID collision.

    Args:
        extra_files: Optional additional YAML files merged on top of the
            global organization mapping.

    Returns:
        Deduplicated list of :class:`~pazufa_corelib.names_model.Organization`
        objects keyed by ``id``.
    """
    files = ORGANIZATIONS_FILES + (extra_files or [])
    org_map: dict[str, Organization] = {}
    for path in files:
        for org in OrganizationFile.from_path(path).names:
            org_map[org.id] = org
    return list(org_map.values())


# =====================================================================
# OrganizationResolver
# =====================================================================


class OrganizationResolver:
    """Resolves raw organization name strings to canonical organization IDs.

    Uses character n-gram cosine similarity for matching, which is robust
    to word-order variants and long compound names. Supports both
    single-query and batch resolution.

    Args:
        extra_files: Optional additional organization YAML files merged on
            top of the global mapping. Later files override earlier entries
            on ID collision.
    """

    def __init__(self, extra_files: list[Path] | None = None) -> None:
        self._organizations: list[Organization] = _load_organizations(extra_files)

        # normalized key → (id, canonical_name, acronym)
        self._key_to_org: dict[str, tuple[str, str, str | None]] = {}
        for org in self._organizations:
            for surface in [org.canonical_name, *org.aliases]:
                key = normalize_name(surface)
                if key:
                    self._key_to_org[key] = (org.id, org.canonical_name, org.acronym)

        self._canonical_name_keys: set[str] = {
            k for o in self._organizations if (k := normalize_name(o.canonical_name))
        }
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
                    "extra_file_count": len(extra_files) if extra_files else 0,
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
        """Check if a query exactly matches a known canonical organization name.

        Aliases are not considered; only canonical names are checked.

        Args:
            query: Raw organization name string to check.

        Returns:
            ``True`` if the normalized query matches a known canonical organization
            name.
        """
        return normalize_name(query) in self._canonical_name_keys

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

    def canonicalize_organization(self, query: str, strict: bool = False) -> str:
        """Resolve a raw organization name to its canonical form.

        Args:
            query: The organization name to resolve.
            strict: If ``True``, unresolved names result in an empty string.
                Defaults to ``False``.

        Returns:
            The canonical name if resolved, the original query if unresolved
            and ``strict=False``, or an empty string if unresolved and
            ``strict=True``.
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
            return ""

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
        4. Return unresolved (score ``0.0``) if nothing clears
           ``_COSINE_MATCH_THRESHOLD``.

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
            # guaranteed: fuzzy_idxs only populated when matrix exists
            assert self._matrix is not None
            q_matrix = _build_matrix(fuzzy_keys, self._vocab)
            # (n_fuzzy, n_canonical)
            scores_matrix = (q_matrix @ self._matrix.T) * 100.0

            for j, i in enumerate(fuzzy_idxs):
                query = queries[i]
                scores = scores_matrix[j]
                best_idx = int(scores.argmax())
                best_score = float(scores[best_idx])

                if best_score < _COSINE_MATCH_THRESHOLD:
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
                        and best_score - second_score <= _COSINE_NEAR_TIE_EPSILON
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
                                "epsilon": _COSINE_NEAR_TIE_EPSILON,
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
