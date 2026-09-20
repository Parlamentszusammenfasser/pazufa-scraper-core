"""Text normalization for parliamentary document processing."""

import html
import re
import unicodedata

from .html_text import html_to_text

# --- Garbled-text detection ---------------------------------------------------

# Latin-Extended-B subset (U+0180–U+024F): stricter signal used in paragraph scoring
_RE_LATIN_EXT_B = re.compile(r"[\u0180-\u024f]")

# C0 control characters and DEL, excluding tab/newline/CR which carry layout:
# a stray NUL (0x00) in particular cannot be stored in a PostgreSQL text column.
_RE_C0_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# C1 control characters (U+0080–U+009F): injected by ASCII+29 font shift
_RE_C1_CONTROLS = re.compile(r"[\x80-\x9f]")

# Invisible characters: C0 controls, the replacement character, and every Unicode
# format character (category Cf) \u2014 soft hyphen, zero-width space and joiners, the
# BOM, and the bidi controls (U+202A\u2013U+202E, U+2066\u2013U+2069) that let a text
# display differently from what it contains. The ranges are Unicode 16.0 and are
# pinned against unicodedata by a test.
_RE_INVISIBLE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd"
    r"\u00ad\u0600-\u0605\u061c\u06dd\u070f\u0890-\u0891\u08e2\u180e"
    r"\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f\ufeff"
    r"\ufff9-\ufffb\U000110BD\U000110CD\U00013430-\U0001343F"
    r"\U0001BCA0-\U0001BCA3\U0001D173-\U0001D17A\U000E0001"
    r"\U000E0020-\U000E007F]"
)

# Unicode line and paragraph separators; NFKC leaves them untouched, so they are
# mapped onto ordinary line breaks with the other line endings
_LINE_SEPARATORS: tuple[tuple[str, str], ...] = (("\u2028", "\n"), ("\u2029", "\n\n"))

# --- Dehyphenation ------------------------------------------------------------

# Line-end hyphen after a word: hyphen-minus or U+2010 (NFKC also turns the
# non-breaking hyphen U+2011 into U+2010). The next word is only looked at, not
# consumed, so a word broken over three lines is rejoined twice.
_RE_LINE_END_HYPHEN = re.compile(r"\b(\w+)([-‐])\n(?=(\w+))")

# Soft hyphen at a line end: always a syllable break
_RE_SOFT_HYPHEN_BREAK = re.compile(r"(\w)­(?:\r\n|\r|\n)(\w)")

# Words after which a line-end hyphen is a suspended hyphen that has to stay
# ("Bundes- und Landesmittel")
_SUSPENDED_HYPHEN_FOLLOWERS: frozenset[str] = frozenset(
    {"und", "oder", "bzw", "sowie", "bis"}
)

# Longest all-caps part that still counts as an acronym next to a line-end
# hyphen ("CDU-geführte", "Vitamin-D"). Anything longer is read as an all-caps
# word that was split across the line ("ZUSAMMEN-\nfassung").
_MAX_ACRONYM_LENGTH = 5

# Multiple spaces/tabs within a line (not newlines)
_RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")

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

    Note that the C1 signal never fires when :func:`normalize_volltext` calls
    this function: its step 5 has already removed those characters. It is kept
    for callers that score text which has not been through the pipeline.

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


def _rejoin_line_end_hyphen(match: re.Match[str]) -> str:
    r"""Rejoin a word split by a line-end hyphen unless the hyphen is real.

    Replacement for ``_RE_LINE_END_HYPHEN``. A suspended hyphen before a
    conjunction stays and the line break becomes a space (``Bundes-\nund`` →
    ``Bundes- und``); keeping the line break would let a later default
    normalization, as ``hash_text`` runs it, join the words after all.

    Otherwise only the line break goes and the hyphen stays when it is next to a
    digit (``20-jährige``), before a capitalised word (``Baden-Württemberg``,
    ``CDU-Fraktion``), after an acronym (``CDU-geführte``, ``EU-weit``) or
    before one (``Vitamin-D``, ``Typ-A``). When both sides are all-caps, an
    all-caps word was split and is joined (``BESCHLUSS-\nEMPFEHLUNG``,
    ``EU-\nROPA``); the same holds for every other syllable break, where hyphen
    and line break both go.
    """
    left, hyphen, right = match.groups()
    if right in _SUSPENDED_HYPHEN_FOLLOWERS:
        return f"{left}{hyphen} "
    left_is_acronym = left.isupper() and 2 <= len(left) <= _MAX_ACRONYM_LENGTH
    right_is_acronym = right.isupper() and len(right) <= _MAX_ACRONYM_LENGTH
    if (
        left[-1].isdigit()
        or right[0].isdigit()
        or (right[0].isupper() and right[1:2].islower())
        or (left_is_acronym and not right.isupper())
        or (right_is_acronym and not left.isupper())
    ):
        return left + hyphen
    return left


# --- Public Functions ---------------------------------------------------------------


def normalize_volltext(text: str) -> str:
    r"""Normalize German fulltext.

    Applies a sequential cleaning pipeline:

    0. Convert HTML markup to plain text (block elements become paragraph
       breaks; ``script``, ``style``, ``head`` and comments are dropped)
    1. HTML entity decoding (``&amp;``, ``&uuml;``, ``&#160;``, …)
    2. NFKC unicode normalisation
    3. Strip invisible characters: zero-width ones (soft hyphen, BOM, ZWJ,
       ZWSP) and the rest of the Unicode format category, including the bidi
       controls that would let the text display differently from its content
    4. Strip C0 control characters and DEL, except ``\\t \\n \\r`` (incl. NUL,
       which PostgreSQL ``text`` columns cannot store)
    5. Strip C1 control characters (U+0080–U+009F)
    6. Normalize line endings to ``\\n``, including the Unicode line and
       paragraph separators U+2028 and U+2029
    7. Rejoin hyphenated line breaks (e.g. ``Landes-\\nregierung`` →
       ``Landesregierung``), keeping real hyphens (``Baden-Württemberg``,
       ``20-jährige``, ``Bundes- und Landesmittel``)
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
    # Before entity decoding, so escaped markup (&lt;b&gt;) stays text.
    text = html_to_text(text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    # Before invisible characters are stripped: without its soft hyphen the
    # word would stay split across the line break.
    text = _RE_SOFT_HYPHEN_BREAK.sub(r"\1\2", text)
    text = _RE_INVISIBLE.sub("", text)
    # Strip C0 controls (incl. NUL) and DEL but keep \t \n \r; a stray NUL
    # would otherwise break the backend's PostgreSQL text insert.
    text = _RE_C0_CONTROLS.sub("", text)
    # C1 controls are not produced by NFKC, so this is a separate stripping pass.
    text = _RE_C1_CONTROLS.sub("", text)
    # Normalize line endings before hyphen-break rejoining, so the pattern
    # always sees bare \n.  Note: this runs before paragraph splitting, so
    # _RE_LINE_END_HYPHEN will not fire across paragraph boundaries (those are
    # separated by \n\s*\n, never a bare word-hyphen-newline-word sequence).
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for separator, replacement in _LINE_SEPARATORS:
        text = text.replace(separator, replacement)
    text = _RE_LINE_END_HYPHEN.sub(_rejoin_line_end_hyphen, text)
    # Collapse intra-line whitespace after rejoining so PDF-extracted extra
    # spaces don't interfere with paragraph splitting (which relies on blank
    # lines, not spaces).
    text = _RE_MULTI_SPACE.sub(" ", text)

    paragraphs = _RE_PARAGRAPH_SPLIT.split(text)
    paragraphs = [p for p in paragraphs if _paragraph_quality_score(p) >= 0.5]
    text = "\n\n".join(paragraphs)

    text = text.replace("<", "\u2039").replace(">", "\u203a")
    return text.strip()
