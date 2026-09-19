"""Name normalization for parliamentary document processing."""

import re
import unicodedata

from .text import _RE_C1_CONTROLS, _RE_INVISIBLE, _RE_MULTI_SPACE

# Punctuation characters that are not word chars or whitespace
_RE_NAME_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

# German umlaut fold applied after NFKC + lowercase (so only lowercase umlauts needed)
_UMLAUT_TABLE: dict[int, str] = {
    ord("ü"): "ue",
    ord("ö"): "oe",
    ord("ä"): "ae",
    ord("ß"): "ss",
}

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


# --- Public Functions ---------------------------------------------------------------


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


def normalize_name_key(text: str) -> str:
    r"""Produce a normalised comparison key for a name string.

    Applies character-level transformations only — no structural changes
    (honorific stripping, token sorting). Intended as the shared base for
    all name resolver preprocessing.

    Pipeline:

    1. NFKC unicode normalisation (ligatures, full-width, NBSP, …)
    2. Strip invisible/zero-width and C1 control characters
    3. Lowercase
    4. German umlaut fold (``ü→ue``, ``ö→oe``, ``ä→ae``, ``ß→ss``)
    5. Strip punctuation (everything that is not ``\\w`` or whitespace)
    6. Collapse multiple spaces/tabs to a single space and strip ends

    Args:
        text: Raw name string.

    Returns:
        Normalised key suitable for exact lookup or as input to a fuzzy
        or n-gram matcher.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _RE_INVISIBLE.sub("", text)
    text = _RE_C1_CONTROLS.sub("", text)
    text = text.lower()
    text = text.translate(_UMLAUT_TABLE)
    text = text.replace("/", " ")  # slash as separator: CDU/CSU, Bündnis 90/Die Grünen
    text = _RE_NAME_PUNCT.sub("", text)
    text = _RE_MULTI_SPACE.sub(" ", text)
    return text.strip()
