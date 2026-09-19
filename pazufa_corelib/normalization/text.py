"""Text normalization for parliamentary document processing."""

import html
import re
import unicodedata

# --- Garbled-text detection ---------------------------------------------------

# Latin-Extended-B subset (U+0180–U+024F): stricter signal used in paragraph scoring
_RE_LATIN_EXT_B = re.compile(r"[\u0180-\u024f]")

# C0 control characters and DEL, excluding tab/newline/CR which carry layout:
# a stray NUL (0x00) in particular cannot be stored in a PostgreSQL text column.
_RE_C0_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# C1 control characters (U+0080–U+009F): injected by ASCII+29 font shift
_RE_C1_CONTROLS = re.compile(r"[\x80-\x9f]")

# Zero-width and invisible characters: soft hyphen, BOM, ZWJ, ZWNJ, ZWSP
_RE_INVISIBLE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\u00ad\u200b\u200c\u200d\ufeff\ufffd]"
)

# Hyphenated line breaks: word-char, hyphen, newline, word-char
_RE_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")

# Multiple spaces/tabs within a line (not newlines)
_RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")

# Punctuation characters that are not word chars or whitespace
_RE_NAME_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

# German umlaut fold applied after NFKC + lowercase (so only lowercase umlauts needed)
_UMLAUT_TABLE: dict[int, str] = {
    ord("ü"): "ue",
    ord("ö"): "oe",
    ord("ä"): "ae",
    ord("ß"): "ss",
}


# German vowels (including umlauts) for consonant-cluster detection
_GERMAN_VOWELS: frozenset[str] = frozenset("aeiouäöüAEIOUÄÖÜ")

# Minimum word count before uppercase penalty is applied.
# Garbled paragraphs from BW PDFs typically span full sentences (≥ 4 words),
# while legitimate all-caps content (headings, labels) is usually shorter.
_MIN_WORDS_FOR_PENALTIES = 4

# --- Paragraph splitting ------------------------------------------------------

_RE_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")

# --- Private helpers ----------------------------------------------------------


def _paragraph_quality_score(paragraph: str) -> float:
    """Score paragraph quality from 0.0 (garbled) to 1.0 (clean).

    Combines four additive penalty signals, each individually capped at 1.0:

    - C1 control character ratio (count / total chars)
    - Latin-Extended-B ratio (count / alpha chars)
    - Long vowel-less word ratio (words ≥5 chars with no German vowel / total words)
    - Excessive uppercase ratio (scaled penalty for ratios above 60%)

    Short paragraphs (fewer than ``_MIN_WORDS_FOR_PENALTIES`` words) are exempt
    from the uppercase penalty to avoid dropping valid all-caps headings.

    Args:
        paragraph: Raw paragraph text to evaluate.

    Returns:
        Quality score in the range [0.0, 1.0], where 1.0 is clean and 0.0 is
        fully garbled.
    """
    text = paragraph.strip()
    if not text:
        return 1.0

    alpha_count = sum(1 for c in text if c.isalpha())

    # Penalty 1: C1 control characters
    c1_penalty = min(1.0, len(_RE_C1_CONTROLS.findall(text)) / len(text))

    # Penalty 2: Latin-Extended-B characters
    ext_b_penalty = min(
        1.0,
        len(_RE_LATIN_EXT_B.findall(text)) / alpha_count if alpha_count else 0.0,
    )

    words = text.split()

    # Penalty 3: Long words without German vowels (consonant clusters)
    long_vowelless = sum(
        1 for w in words if len(w) >= 5 and not any(c in _GERMAN_VOWELS for c in w)
    )
    vowelless_penalty = min(1.0, long_vowelless / len(words)) if words else 0.0

    # Penalty 4: Excessive uppercase (penalises ratios above 60%)
    # Skipped for short paragraphs (section headers are legitimately all-caps).
    if len(words) < _MIN_WORDS_FOR_PENALTIES:
        upper_penalty = 0.0
    else:
        upper_ratio = (
            sum(1 for c in text if c.isupper()) / alpha_count if alpha_count else 0.0
        )
        upper_penalty = max(0.0, (upper_ratio - 0.6) / 0.4)

    score = 1.0 - (c1_penalty + ext_b_penalty + vowelless_penalty + upper_penalty)
    return max(0.0, min(1.0, score))


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


def normalize_volltext(text: str) -> str:
    r"""Normalize German fulltext.

    Applies a sequential cleaning pipeline:

    1. HTML entity decoding (``&amp;``, ``&uuml;``, ``&#160;``, …)
    2. NFKC unicode normalisation
    3. Strip invisible/zero-width characters (soft hyphen, BOM, ZWJ, ZWSP)
    4. Strip C0 control characters and DEL, except ``\\t \\n \\r`` (incl. NUL,
       which PostgreSQL ``text`` columns cannot store)
    5. Strip C1 control characters (U+0080–U+009F)
    6. Normalize line endings to ``\\n``
    7. Rejoin hyphenated line breaks (e.g. ``Landes-\\nregierung`` →
       ``Landesregierung``)
    8. Collapse multiple spaces/tabs within a line to a single space
    9. Remove paragraphs with quality score < 0.5
    10. Replace ``<`` / ``>`` with guillemets ‹ › to neutralize XSS triggers

    Step 1 is a no-op on plain text containing no entity sequences, so
    applying this function to PDF-extracted text has no side effects.

    Args:
        text: Raw extracted text from a PDF parser or HTML source.

    Returns:
        Cleaned text with garbled paragraphs removed and whitespace normalized.
        Returns an empty string if the input is empty or all paragraphs are
        filtered out.
    """
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = _RE_INVISIBLE.sub("", text)
    # Strip C0 controls (incl. NUL) and DEL but keep \t \n \r; a stray NUL
    # would otherwise break the backend's PostgreSQL text insert.
    text = _RE_C0_CONTROLS.sub("", text)
    # C1 controls are not produced by NFKC, so this is a separate stripping pass.
    text = _RE_C1_CONTROLS.sub("", text)
    # Normalize line endings before hyphen-break rejoining, so the pattern
    # always sees bare \n.  Note: this runs before paragraph splitting, so
    # _RE_HYPHEN_BREAK will not fire across paragraph boundaries (those are
    # separated by \n\s*\n, never a bare word-hyphen-newline-word sequence).
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _RE_HYPHEN_BREAK.sub(r"\1\2", text)
    # Collapse intra-line whitespace after rejoining so PDF-extracted extra
    # spaces don't interfere with paragraph splitting (which relies on blank
    # lines, not spaces).
    text = _RE_MULTI_SPACE.sub(" ", text)

    paragraphs = _RE_PARAGRAPH_SPLIT.split(text)
    paragraphs = [p for p in paragraphs if _paragraph_quality_score(p) >= 0.5]
    text = "\n\n".join(paragraphs)

    text = text.replace("<", "\u2039").replace(">", "\u203a")
    return text.strip()
