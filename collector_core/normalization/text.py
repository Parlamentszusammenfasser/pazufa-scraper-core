"""Text and date normalization for parliamentary document processing."""

import re
import unicodedata
from datetime import date

# --- Garbled-text detection ---------------------------------------------------

# Latin-Extended characters (U+0100–U+024F): appear in broken ToUnicode CMap fonts
_RE_LATIN_EXTENDED = re.compile(r"[\u0100-\u024f]")
# Latin-Extended-B subset (U+0180–U+024F): stricter signal used in paragraph scoring
_RE_LATIN_EXT_B = re.compile(r"[\u0180-\u024f]")

# C1 control characters (U+0080–U+009F): injected by ASCII+29 font shift
_RE_C1_CONTROLS = re.compile(r"[\x80-\x9f]")

# German vowels (including umlauts) for consonant-cluster detection
_GERMAN_VOWELS: frozenset[str] = frozenset("aeiouäöüAEIOUÄÖÜ")

# --- Paragraph splitting ------------------------------------------------------

_RE_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")

# --- Date parsing -------------------------------------------------------------

_RE_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_RE_GERMAN_DOT = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
_RE_GERMAN_LONG = re.compile(r"^(\d{1,2})\.?\s*([A-Za-zäöüÄÖÜ]+)\.?\s+(\d{4})$")

_GERMAN_MONTHS: dict[str, int] = {
    # Full names
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
    # Abbreviations (trailing dot consumed by regex, not included here)
    "jan": 1,
    "feb": 2,
    "mär": 3,
    "mrz": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "okt": 10,
    "nov": 11,
    "dez": 12,
}


# --- Private helpers ----------------------------------------------------------


def _is_garbled(text: str) -> bool:
    """Return True if >5% of alphabetic characters are Latin-Extended (U+0100–U+024F).

    This detects the broken ToUnicode CMap pattern found in some BW Landtag PDFs
    where glyph IDs are incorrectly mapped to U+0100–U+024F codepoints.
    """
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count == 0:
        return False
    ext_count = len(_RE_LATIN_EXTENDED.findall(text))
    return ext_count / alpha_count > 0.05


def _paragraph_quality_score(paragraph: str) -> float:
    """Score paragraph quality from 0.0 (garbled) to 1.0 (clean).

    Combines four additive penalty signals:
    - C1 control character ratio (count / total chars)
    - Latin-Extended-B ratio (count / alpha chars)
    - Long vowel-less words ratio (words ≥5 chars / total words)
    - Excessive uppercase ratio (scaled penalty above 60% threshold)
    """
    text = paragraph.strip()
    if not text:
        return 1.0

    alpha_count = sum(1 for c in text if c.isalpha())

    # Penalty 1: C1 control characters
    c1_penalty = len(_RE_C1_CONTROLS.findall(text)) / len(text)

    # Penalty 2: Latin-Extended-B characters
    ext_b_penalty = len(_RE_LATIN_EXT_B.findall(text)) / alpha_count if alpha_count else 0.0

    # Penalty 3: Long words without German vowels (consonant clusters)
    words = text.split()
    long_vowelless = sum(
        1 for w in words if len(w) >= 5 and not any(c in _GERMAN_VOWELS for c in w)
    )
    vowelless_penalty = long_vowelless / len(words) if words else 0.0

    # Penalty 4: Excessive uppercase (penalises ratios above 60%)
    upper_ratio = sum(1 for c in text if c.isupper()) / alpha_count if alpha_count else 0.0
    upper_penalty = max(0.0, (upper_ratio - 0.6) / 0.4)

    score = 1.0 - (c1_penalty + ext_b_penalty + vowelless_penalty + upper_penalty)
    return max(0.0, min(1.0, score))


# --- Public Functions ---------------------------------------------------------------


def normalise_volltext(text: str) -> str:
    """Normalise German fulltext extracted from PDFs.

    1. NFKC unicode normalisation
    2. Strip C1 control characters (U+0080–U+009F)
    3. Normalise line endings to \\n
    4. Remove paragraphs with quality score < 0.5
    5. Replace ``<`` / ``>`` with guillemets ‹ › to neutralise XSS triggers
    """
    text = unicodedata.normalize("NFKC", text)
    text = _RE_C1_CONTROLS.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = _RE_PARAGRAPH_SPLIT.split(text)
    paragraphs = [p for p in paragraphs if _paragraph_quality_score(p) >= 0.5]
    text = "\n\n".join(paragraphs)

    text = text.replace("<", "\u2039").replace(">", "\u203a")
    return text.strip()


def normalise_datum(text: str) -> str:
    """Parse a German or ISO date string to ISO 8601 (YYYY-MM-DD).

    Supported formats:
    - ``02.04.2026`` / ``2.4.2026``  — German dot notation
    - ``2. April 2026``              — German long format
    - ``2026-04-02``                 — ISO 8601 passthrough

    Raises ``ValueError`` for unparseable or calendar-invalid dates.
    """
    text = text.strip()

    m = _RE_ISO_DATE.match(text)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(year, month, day).isoformat()

    m = _RE_GERMAN_DOT.match(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(year, month, day).isoformat()

    m = _RE_GERMAN_LONG.match(text)
    if m:
        day, month_name, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month_num = _GERMAN_MONTHS.get(month_name)
        if month_num is None:
            raise ValueError(f"Unknown German month name: {m.group(2)!r}")
        return date(year, month_num, day).isoformat()

    raise ValueError(f"Unparseable date: {text!r}")
