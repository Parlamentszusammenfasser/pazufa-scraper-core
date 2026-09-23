"""Date normalization for parliamentary document processing."""

import re
import unicodedata
from datetime import date

_RE_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_RE_GERMAN_DOT = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
_RE_GERMAN_NONSTANDARD = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2})$")
_RE_GERMAN_LONG = re.compile(r"^(\d{1,2})\.?\s*([A-Za-zäöüÄÖÜ]+)\.?\s+(\d{4})$")

_GERMAN_MONTHS: dict[str, int] = {
    # Full names
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,  # no standard German abbreviation
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


def normalize_datum(text: str) -> str:
    """Parse a German or ISO date string to ISO 8601 (YYYY-MM-DD).

    Supported input formats:

    - ``02.04.2026`` / ``2.4.2026`` — German dot notation
    - ``2. April 2026``             — German long format (full and abbreviated month
      names)
    - ``02.04.26`` / ``2.4.26``     — Not standardized, but used in some documents
    - ``2026-04-02``                — ISO 8601 passthrough

    Unicode spaces (e.g. U+00A0 NBSP, U+202F narrow no-break space) are
    collapsed via NFKC before matching, as they commonly appear in
    PDF-extracted date strings.

    Args:
        text: Date string in one of the supported formats. Leading and trailing
            whitespace is ignored.

    Returns:
        ISO 8601 date string in ``YYYY-MM-DD`` format.

    Raises:
        ValueError: If the input does not match any supported format or
            represents a calendar-invalid date (e.g. 29 Feb on a non-leap year).
    """
    text = unicodedata.normalize("NFKC", text).strip()

    m = _RE_ISO_DATE.match(text)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(year, month, day).isoformat()

    m = _RE_GERMAN_DOT.match(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(year, month, day).isoformat()

    m = _RE_GERMAN_NONSTANDARD.match(text)
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
