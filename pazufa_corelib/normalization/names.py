"""Name normalisation and resolution for authors and organisations."""

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
    Organisation,
    OrganisationFile,
    OrganisationIDResolution,
)
from pazufa_corelib.normalization._fuzzy import fuzzy_resolve
from pazufa_corelib.normalization.text import normalize_name_key

MAPPINGS_DIR: Path = Path(__file__).parent / "mappings"
"""Path to the mappings directory."""

AUTHORS_FILES: list[Path] = [MAPPINGS_DIR / "authors.yaml"]
"""Canonical list of paths to the global author files."""

ORGANISATIONS_FILES: list[Path] = [
    MAPPINGS_DIR / "parteien.yaml",
    MAPPINGS_DIR / "organisations.yaml",
]
"""Canonical list of paths to the global organisation files."""

_EXACT_MATCH_THRESHOLD: float = 100.0
_FUZZY_MATCH_THRESHOLD: float = 90.0
_NEAR_TIE_EPSILON: float = 1.0

_NGRAM_SIZE: int = 3
_COSINE_MATCH_THRESHOLD: float = 0.80
_COSINE_NEAR_TIE_EPSILON: float = 0.02

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
    """Normalise a person or organisation name to a stable comparison key.

    Pipeline:

    1. Strip honorifics and post-nominals (``Dr.``, ``Prof.``, ``MdB``, …)
    2. Apply :func:`normalize_name_key` (NFKC, umlaut fold, lowercase,
       strip punctuation, collapse whitespace)
    3. Token-sort — ``"Maria Müller"`` and ``"Müller, Maria"`` produce the
       same key

    Args:
        raw: Raw name string, e.g. from scraped parliamentary data.

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


def _canonicalise_names(
    raw_names: list[str],
    canonical_keys: list[str],
    key_to_author: dict[str, tuple[str, str]],
    strict: bool = False,
    cutoff: float = _FUZZY_MATCH_THRESHOLD,
) -> list[AuthorIDResolution]:
    """Fuzzy-match raw name strings against canonical normalised keys.

    Each raw name is matched to its closest canonical key using
    ``WRatio`` scoring. Near-tie matches are logged as warnings.

    Args:
        raw_names: Name strings to resolve.
        canonical_keys: Pre-normalised keys to match against.
        key_to_author: Mapping of normalised key to ``(id, canonical_name)``.
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
        processor=normalize_name,  # idempotent on pre-normalised keys
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
    """Resolves raw author name strings to canonical author IDs.

    Loads the global author YAML and any caller-supplied extra files,
    builds a normalised-key lookup, and resolves queries via exact match
    first, then rapidfuzz ``WRatio`` fuzzy matching.

    Args:
        extra_files: Optional additional author YAML files merged on top
            of the global mapping. Later files override earlier entries
            on ID collision.
    """

    def __init__(self, extra_files: list[Path] | None = None) -> None:
        self._authors: list[Author] = _load_authors(extra_files)

        # normalised key → (id, canonical_name)
        self._key_to_author: dict[str, tuple[str, str]] = {}
        for author in self._authors:
            for surface in [author.canonical_name, *author.aliases]:
                key = normalize_name(surface)
                if key:
                    self._key_to_author[key] = (author.id, author.canonical_name)

        self._author_ids: set[str] = {a.id for a in self._authors}
        self._canonical_keys: list[str] = list(self._key_to_author)

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "AuthorResolver: %d authors, %d canonical keys | "
                "_key_to_author %d B (shallow), _author_ids %d B (shallow), "
                "_canonical_keys %d B (shallow)",
                len(self._authors),
                len(self._canonical_keys),
                sys.getsizeof(self._key_to_author),
                sys.getsizeof(self._author_ids),
                sys.getsizeof(self._canonical_keys),
            )

    # =====================================================================
    # Author actions
    # =====================================================================

    def check_author(self, query: str) -> bool:
        """Check whether a query string exactly matches a known author.

        Args:
            query: Raw name string to check.

        Returns:
            ``True`` if the normalised query matches a known author key.
        """
        return normalize_name(query) in self._key_to_author

    def fuzzy_check_author(self, query: str) -> bool:
        """Fuzzy-match a name string against the known author vocabulary.

        Uses :func:`_canonicalise_names` to find the best fuzzy match.

        Args:
            query: Raw name string to check.

        Returns:
            ``True`` if the name matched a known author above the fuzzy
            cutoff, ``False`` otherwise.
        """
        result = _canonicalise_names(
            [normalize_name(query)], self._canonical_keys, self._key_to_author
        )[0]
        LOGGER.debug("Fuzzy check returned: %s", result)
        return result.matched

    def canonicalise_authors(
        self, queries: list[str], strict: bool = False
    ) -> list[str]:
        """Canonicalise a list of raw name strings to author IDs.

        Args:
            queries: Raw name strings to resolve.
            strict: If ``True``, unmatched names are dropped; if ``False``,
                they are returned as empty strings.

        Returns:
            List of resolved canonical author IDs, in the same order as
            *queries* (unless ``strict=True`` drops some).
        """
        resolved = _canonicalise_names(
            [normalize_name(q) for q in queries],
            self._canonical_keys,
            self._key_to_author,
            strict=strict,
        )
        return [r.resolved_id for r in resolved]

    def resolve(self, query: str) -> AuthorIDResolution:
        """Resolve a single raw author name to a canonical entry.

        Resolution order:

        1. Normalise the query with :func:`normalize_name`.
        2. Exact lookup in the normalised-key index.
        3. Fuzzy match via :func:`_canonicalise_names`.
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

        return _canonicalise_names(
            [query_key], self._canonical_keys, self._key_to_author
        )[0]


# =====================================================================
# N-gram helpers
# =====================================================================


def _ngrams(text: str, n: int = _NGRAM_SIZE) -> list[str]:
    """Return padded character n-grams for *text*.

    Pads with a single space on each side so short tokens still produce
    edge n-grams (e.g. ``"FDP"`` → ``" FD"``, ``"FDP"``, ``"DP "``).
    """
    padded = f" {text} "
    return [padded[i : i + n] for i in range(len(padded) - n + 1)]


def _build_vocab(keys: list[str], n: int = _NGRAM_SIZE) -> dict[str, int]:
    """Build a trigram vocabulary from a list of normalised keys.

    Args:
        keys: Pre-normalised name strings.
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


def _vectorise(key: str, vocab: dict[str, int], n: int = _NGRAM_SIZE) -> np.ndarray:
    """Vectorise a normalised key into an L2-normalised n-gram count vector.

    N-grams not present in *vocab* are silently ignored, so the function
    is safe to call on query strings that contain unseen n-grams.

    Args:
        key: Pre-normalised name string.
        vocab: N-gram vocabulary produced by :func:`_build_vocab`.
        n: N-gram size, must match the size used to build *vocab*.

    Returns:
        Float32 array of shape ``(len(vocab),)``, L2-normalised. Returns
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
    """Build an L2-normalised n-gram matrix for a list of keys.

    Args:
        keys: Pre-normalised name strings (one row per key).
        vocab: N-gram vocabulary produced by :func:`_build_vocab`.
        n: N-gram size.

    Returns:
        Float32 array of shape ``(len(keys), len(vocab))`` with each row
        L2-normalised. Cosine similarity between any query vector and
        this matrix is then a plain dot product.
    """
    return np.vstack([_vectorise(k, vocab, n) for k in keys])


# =====================================================================
# Organisation loader
# =====================================================================


def _load_organisations(extra_files: list[Path] | None = None) -> list[Organisation]:
    """Load and merge organisations from the global file and any extra files.

    Files are merged in order; later entries override earlier ones on
    ID collision.

    Args:
        extra_files: Optional additional YAML files merged on top of the
            global organisation mapping.

    Returns:
        Deduplicated list of :class:`~pazufa_corelib.names_model.Organisation`
        objects keyed by ``id``.
    """
    files = ORGANISATIONS_FILES + (extra_files or [])
    org_map: dict[str, Organisation] = {}
    for path in files:
        for org in OrganisationFile.from_path(path).names:
            org_map[org.id] = org
    return list(org_map.values())


# =====================================================================
# OrganisationResolver
# =====================================================================


class OrganisationResolver:
    """Resolves raw organisation name strings to canonical organisation IDs.

    Uses character n-gram cosine similarity for matching, which is robust
    to word-order variants and long compound names. Supports both
    single-query and batch resolution.

    Args:
        extra_files: Optional additional organisation YAML files merged on
            top of the global mapping. Later files override earlier entries
            on ID collision.
    """

    def __init__(self, extra_files: list[Path] | None = None) -> None:
        self._organisations: list[Organisation] = _load_organisations(extra_files)

        # normalised key → (id, canonical_name, akronym)
        self._key_to_org: dict[str, tuple[str, str, str | None]] = {}
        for org in self._organisations:
            for surface in [org.canonical_name, *org.aliases]:
                key = normalize_name(surface)
                if key:
                    self._key_to_org[key] = (org.id, org.canonical_name, org.akronym)

        self._org_ids: set[str] = {o.id for o in self._organisations}
        self._id_to_akronym: dict[str, str | None] = {
            o.id: o.akronym for o in self._organisations
        }
        self._akronym_to_orgs: dict[str, list[Organisation]] = {}
        for org in self._organisations:
            if org.akronym is not None:
                self._akronym_to_orgs.setdefault(org.akronym, []).append(org)
        self._canonical_keys: list[str] = list(self._key_to_org)

        # pre-build n-gram index
        self._vocab: dict[str, int] = _build_vocab(self._canonical_keys)
        self._matrix: np.ndarray = (
            _build_matrix(self._canonical_keys, self._vocab)
            if self._canonical_keys
            else np.empty((0, 0), dtype=np.float32)
        )

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "OrganisationResolver: %d organisations, %d canonical keys, "
                "%d vocab entries | "
                "matrix %s dtype=%s (%d B exact) | "
                "_key_to_org %d B (shallow), _vocab %d B (shallow), "
                "_id_to_akronym %d B (shallow), _akronym_to_orgs %d B (shallow)",
                len(self._organisations),
                len(self._canonical_keys),
                len(self._vocab),
                self._matrix.shape,
                self._matrix.dtype,
                self._matrix.nbytes,
                sys.getsizeof(self._key_to_org),
                sys.getsizeof(self._vocab),
                sys.getsizeof(self._id_to_akronym),
                sys.getsizeof(self._akronym_to_orgs),
            )

    # =====================================================================
    # Organisation actions
    # =====================================================================

    def check_organisation(self, query: str) -> bool:
        """Check whether a query string exactly matches a known organisation.

        Args:
            query: Raw organisation name string to check.

        Returns:
            ``True`` if the normalised query matches a known organisation key.
        """
        return normalize_name(query) in self._key_to_org

    def get_akronym(self, org_id: str) -> str | None:
        """Return the akronym for a known organisation ID, or ``None``.

        Args:
            org_id: Canonical slug ID, e.g. ``"spd"``.

        Returns:
            The akronym string if the organisation has one, ``None`` if it
            has none or if *org_id* is not in the vocabulary.
        """
        return self._id_to_akronym.get(org_id)

    def get_organisations_by_akronym(self, akronym: str) -> list[Organisation]:
        """Return all organisations that carry the given akronym.

        The lookup is case-sensitive and matches the akronym exactly as stored
        in the YAML (e.g. ``"SPD"``, not ``"spd"``).

        Args:
            akronym: Abbreviation to look up, e.g. ``"CDU"``.

        Returns:
            List of matching :class:`~pazufa_corelib.names_model.Organisation`
            objects. Empty list if no organisation carries this akronym.
        """
        return list(self._akronym_to_orgs.get(akronym, []))

    def fuzzy_check_organisation(self, query: str) -> bool:
        """Fuzzy-match a name string against the known organisation vocabulary.

        Uses n-gram cosine similarity via :meth:`resolve_batch`.

        Args:
            query: Raw organisation name string to check.

        Returns:
            ``True`` if the name matched a known organisation above the cosine
            threshold, ``False`` otherwise.
        """
        result = self.resolve_batch([query])[0]
        LOGGER.debug("Fuzzy check returned: %s", result)
        return result.matched

    def canonicalise_organisations(
        self, queries: list[str], strict: bool = False
    ) -> list[str]:
        """Canonicalise a list of raw organisation name strings to IDs.

        Args:
            queries: Raw organisation name strings to resolve.
            strict: If ``True``, unmatched names are dropped; if ``False``,
                they are returned as empty strings.

        Returns:
            List of resolved canonical organisation IDs, in the same order
            as *queries* (unless ``strict=True`` drops some).
        """
        resolved = self.resolve_batch(queries)
        if strict:
            return [r.resolved_id for r in resolved if r.matched]
        return [r.resolved_id for r in resolved]

    def resolve(self, query: str) -> OrganisationIDResolution:
        """Resolve a single raw organisation name to a canonical entry.

        Resolution order:

        1. Normalise the query with :func:`normalize_name`.
        2. Exact lookup in the normalised-key index.
        3. N-gram cosine similarity against the canonical matrix.
        4. Return unresolved (score ``0.0``) if nothing clears
           ``_COSINE_MATCH_THRESHOLD``.

        Args:
            query: Raw organisation name string.

        Returns:
            :class:`~pazufa_corelib.names_model.OrganisationIDResolution`
            with the best match found, or an unresolved result when no
            match cleared the threshold.
        """
        return self.resolve_batch([query])[0]

    def resolve_batch(self, queries: list[str]) -> list[OrganisationIDResolution]:
        """Resolve a batch of raw organisation names in a single matmul.

        Args:
            queries: Raw organisation name strings.

        Returns:
            List of :class:`~pazufa_corelib.names_model.OrganisationIDResolution`
            in the same order as *queries*.
        """
        results: list[OrganisationIDResolution] = []

        for query in queries:
            query_key = normalize_name(query)

            if not query_key:
                results.append(
                    OrganisationIDResolution(
                        original_name=query,
                        resolved_id="",
                        canonical_name=query,
                        score=0.0,
                    )
                )
                continue

            # --- exact match --------------------------------------------
            if query_key in self._key_to_org:
                org_id, canonical_name, akronym = self._key_to_org[query_key]
                results.append(
                    OrganisationIDResolution(
                        original_name=query,
                        resolved_id=org_id,
                        canonical_name=canonical_name,
                        akronym=akronym,
                        score=1.0,
                    )
                )
                continue

            # --- cosine match -------------------------------------------
            if not self._canonical_keys:
                results.append(
                    OrganisationIDResolution(
                        original_name=query,
                        resolved_id="",
                        canonical_name=query,
                        score=0.0,
                    )
                )
                continue

            q_vec = _vectorise(query_key, self._vocab)
            scores = self._matrix @ q_vec

            best_idx = int(scores.argmax())
            best_score = float(scores[best_idx])

            if best_score < _COSINE_MATCH_THRESHOLD:
                results.append(
                    OrganisationIDResolution(
                        original_name=query,
                        resolved_id="",
                        canonical_name=query,
                        score=0.0,
                    )
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
                        "Near-tie for %r: %r (%.4f) vs %r (%.4f),"
                        " delta=%.4f <= epsilon=%.4f",
                        query,
                        self._canonical_keys[best_idx],
                        best_score,
                        self._canonical_keys[second_idx],
                        second_score,
                        best_score - second_score,
                        _COSINE_NEAR_TIE_EPSILON,
                    )

            org_id, canonical_name, akronym = self._key_to_org[
                self._canonical_keys[best_idx]
            ]
            results.append(
                OrganisationIDResolution(
                    original_name=query,
                    resolved_id=org_id,
                    canonical_name=canonical_name,
                    akronym=akronym,
                    score=best_score,
                )
            )

        return results
