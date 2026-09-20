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

# --- HTML tag stripping -------------------------------------------------------

# HTML element names, one set per role, i.e. per what happens to the tag. Each name
# belongs to exactly one role. The long sets are wrapped by hand (fmt: off), since
# the formatter would put every name on a line of its own.

# Start and end tag become a blank line (paragraph break)
# fmt: off
_HTML_BLOCK_ELEMENTS: frozenset[str] = frozenset({
    "address", "article", "aside", "blockquote", "body", "caption", "center", "dd",
    "details", "dialog", "div", "dl", "dt", "fieldset", "figcaption", "figure",
    "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr",
    "html", "main", "nav", "ol", "p", "pre", "section", "summary", "table", "ul",
})
# fmt: on

# Start tag begins a new line or a new table cell; the end tag is removed
_HTML_LINE_ELEMENTS: frozenset[str] = frozenset({"br", "li", "tr", "option"})
_HTML_CELL_ELEMENTS: frozenset[str] = frozenset({"td", "th"})

# Removed together with their content (see _RE_HTML_SPAN_OPENER). The document
# head is removed there too, but by a rule of its own, so "head" is not listed.
_HTML_ELEMENTS_WITHOUT_TEXT: frozenset[str] = frozenset(
    {"math", "noscript", "script", "style", "svg", "template"}
)

# Tag is removed without leaving a gap: inline elements, but also elements such
# as tbody or title whose tags need no separator
# fmt: off
_HTML_INLINE_ELEMENTS: frozenset[str] = frozenset({
    "a", "abbr", "acronym", "area", "audio", "b", "base", "bdi", "bdo", "big", "button",
    "canvas", "cite", "code", "col", "colgroup", "data", "datalist", "del", "dfn",
    "dir", "em", "embed", "font", "frame", "frameset", "i", "iframe", "img", "input",
    "ins", "kbd", "label", "legend", "link", "map", "mark", "menu", "meta", "meter",
    "nobr", "noframes", "object", "optgroup", "output", "param", "picture",
    "progress", "q", "rp", "rt", "ruby", "s", "samp", "search", "select", "slot",
    "small", "source", "span", "strike", "strong", "sub", "sup", "tbody", "textarea",
    "tfoot", "thead", "time", "title", "track", "tt", "u", "var", "video", "wbr",
})
# fmt: on

# All known element names. Only these, plus namespaced and custom element names,
# count as tags, so angle-bracket text such as <poststelle@lfdi.bwl.de> or
# "a < b" survives as text.
_HTML_ELEMENTS: frozenset[str] = (
    _HTML_BLOCK_ELEMENTS
    | _HTML_LINE_ELEMENTS
    | _HTML_CELL_ELEMENTS
    | _HTML_ELEMENTS_WITHOUT_TEXT
    | {"head"}
    | _HTML_INLINE_ELEMENTS
)

# HTML whitespace is ASCII only; NBSP is left for NFKC to turn into a space
_RE_HTML_WHITESPACE = re.compile(r"[ \t\n\r\f]+")

# Evidence that the input really is an HTML document, not text that merely
# contains a stray tag. Only then do HTML whitespace rules apply: in text from a
# PDF, line breaks are content and must survive.
_RE_HTML_DOCUMENT = re.compile(
    r"<!doctype\s+html|<html[\s>]|<body[\s>]|<br\s*/?>"
    r"|</(?:p|div|span|a|b|i|strong|em|td|th|tr|li|ul|ol|table|h[1-6])\s*>",
    re.IGNORECASE,
)

# Openers of constructs removed together with their content: comments (incl.
# Word's <!--[if gte mso 9]>…<![endif]--> blocks), CDATA sections, elements
# without text and the document head. The matched group name (or element name)
# selects the closer in _HTML_SPAN_CLOSERS.
_RE_HTML_SPAN_OPENER = re.compile(
    r"(?P<comment><!--)|(?P<cdata><!\[CDATA\[)"
    rf"|<(?P<element>{'|'.join(sorted(_HTML_ELEMENTS_WITHOUT_TEXT))})\b[^<>]*>"
    r"|(?P<head><head\b[^<>]*>)",
    re.IGNORECASE,
)
_HTML_SPAN_CLOSERS: dict[str, re.Pattern[str]] = {
    "comment": re.compile(r"-->"),
    "cdata": re.compile(r"\]\]>"),
    # an omitted </head> ends where <body> starts
    "head": re.compile(r"</head\s*>|(?=<body[\s>])", re.IGNORECASE),
    **{
        name: re.compile(rf"</{name}\s*>", re.IGNORECASE)
        for name in _HTML_ELEMENTS_WITHOUT_TEXT
    },
}

# Word's <![if …]> / <![endif]> markers, doctype, XML declaration
_RE_HTML_DECLARATION = re.compile(
    r"<!\[(?:if\b[^\]<>]*|endif)\]>|<!doctype[^<>]*>|<\?xml[^<>]*\?>",
    re.IGNORECASE,
)

# Attribute list that ends a start tag; quoted values may contain ">"
_HTML_TAG_ATTRIBUTES = (
    r"""(?:\s+[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>=`]+))?)*\s*/?>"""
)

# Start or end tag of a known element or of a namespaced one (Word's <o:p>).
# Group 1 is "/" for end tags, group 2 the element name.
_RE_HTML_TAG = re.compile(
    r"<(/?)((?:"
    + "|".join(sorted(_HTML_ELEMENTS, key=len, reverse=True))
    + r")(?![\w:-])|[a-z][a-z0-9]*(?::[\w.-]+)+)"
    + _HTML_TAG_ATTRIBUTES,
    re.IGNORECASE,
)

# Start or end tag of a custom element (<my-widget>). The same shape also fits
# ordinary text in angle brackets (<Baden-Württemberg>), so every match is put to
# _replace_custom_element_tags, which needs the attribute list to decide.
_RE_HTML_CUSTOM_TAG = re.compile(
    rf"<(/?)([a-z][a-z0-9]*(?:-[\w.-]+)+)(?P<attributes>{_HTML_TAG_ATTRIBUTES})",
    re.IGNORECASE,
)

# Any end tag; evidence that a custom element name is markup rather than text
_RE_HTML_CLOSING_TAG = re.compile(r"</([a-z][\w.:-]*)\s*>", re.IGNORECASE)

# Spaces left around the line breaks inserted for block and line elements
_RE_HTML_NEWLINE_PADDING = re.compile(r"[ \t]*\n[ \t]*")

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


def _html_tag_separator(match: re.Match[str]) -> str:
    """Return the text that replaces a tag matched by ``_RE_HTML_TAG``."""
    is_end_tag, name = bool(match.group(1)), match.group(2).lower()
    if name in _HTML_BLOCK_ELEMENTS:
        return "\n\n"
    if not is_end_tag and name in _HTML_LINE_ELEMENTS:
        return "\n"
    if not is_end_tag and name in _HTML_CELL_ELEMENTS:
        return " "
    return ""


def _remove_html_spans(text: str) -> str:
    """Remove comments, CDATA, the head and elements without text, with content.

    Scans left to right, so whichever construct opens first wins (a ``<!--``
    inside a script is script content). An opener without a closer is left in
    place, and its kind is skipped from then on: no later opener of that kind
    can be closed either. This keeps the scan linear where a lazy
    ``<x>.*?</x>`` regex would rescan the rest of the text for every opener.

    Args:
        text: HTML with whitespace already collapsed.

    Returns:
        The HTML without those constructs.
    """
    parts: list[str] = []
    unclosed: set[str] = set()
    kept_from = scan_from = 0
    while (opener := _RE_HTML_SPAN_OPENER.search(text, scan_from)) is not None:
        kind = opener.lastgroup or ""
        if kind == "element":
            kind = opener.group("element").lower()
        closer = None
        if kind not in unclosed:
            closer = _HTML_SPAN_CLOSERS[kind].search(text, opener.end())
        if closer is None:
            unclosed.add(kind)
            scan_from = opener.end()
            continue
        parts.append(text[kept_from : opener.start()])
        kept_from = scan_from = closer.end()
    parts.append(text[kept_from:])
    return "".join(parts)


def _replace_custom_element_tags(text: str) -> str:
    """Remove the tags of custom elements, but only where they really are tags.

    A hyphenated name in angle brackets has the shape of a custom element
    (``<my-widget>``), but so does ordinary text (``<Baden-Württemberg>``,
    ``<vor-nachname>``). Removing the latter would silently swallow content, so
    a name counts as markup only when the document backs it up: the tag carries
    attributes, or the text closes it somewhere. Custom element names are
    lowercase per the HTML specification, so a capitalised name is text.

    Args:
        text: HTML whose known and namespaced tags have already been replaced.

    Returns:
        The text with genuine custom element tags removed.
    """
    closed = {m.group(1).lower() for m in _RE_HTML_CLOSING_TAG.finditer(text)}

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        has_attributes = match.group("attributes").strip() not in (">", "/>")
        if name.islower() and (name in closed or has_attributes):
            return _html_tag_separator(match)
        return match.group(0)

    return _RE_HTML_CUSTOM_TAG.sub(replace, text)


def _strip_html_tags(text: str) -> str:
    """Convert HTML markup to plain text for :func:`normalize_volltext`.

    Drops comments, declarations and non-text elements (``script``, ``style``,
    ``head``, …), turns block elements into blank lines, ``br`` / ``li`` /
    ``tr`` into line breaks and table cells into spaces, and removes all other
    tags without leaving a gap. Entities stay encoded for the decoding step that
    follows, so escaped markup such as ``&lt;b&gt;`` remains text.

    HTML whitespace rules (line breaks and indentation in the source are not
    text) are applied only to input that looks like an HTML document. In text
    from a PDF a line break is content, and collapsing it would destroy the
    paragraphs that the quality filter and dehyphenation rely on.

    Args:
        text: Raw HTML, or text that contains no markup at all.

    Returns:
        Text without markup, with paragraph structure expressed as newlines.
    """
    if _RE_HTML_DOCUMENT.search(text):
        text = _RE_HTML_WHITESPACE.sub(" ", text)
    text = _remove_html_spans(text)
    text = _RE_HTML_DECLARATION.sub("", text)
    text = _RE_HTML_TAG.sub(_html_tag_separator, text)
    text = _replace_custom_element_tags(text)
    return _RE_HTML_NEWLINE_PADDING.sub("\n", text)


# --- Public Functions ---------------------------------------------------------------


def normalize_volltext(text: str) -> str:
    r"""Normalize German fulltext.

    Applies a sequential cleaning pipeline:

    0. Convert HTML markup to plain text (block elements become paragraph
       breaks; ``script``, ``style``, ``head`` and comments are dropped)
    1. HTML entity decoding (``&amp;``, ``&uuml;``, ``&#160;``, …)
    2. NFKC unicode normalisation
    3. Strip invisible/zero-width characters (soft hyphen, BOM, ZWJ, ZWSP)
    4. Strip C0 control characters and DEL, except ``\\t \\n \\r`` (incl. NUL,
       which PostgreSQL ``text`` columns cannot store)
    5. Strip C1 control characters (U+0080–U+009F)
    6. Normalize line endings to ``\\n``
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
    text = _strip_html_tags(text)
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
