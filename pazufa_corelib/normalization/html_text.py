"""Conversion of HTML markup to plain text.

Used by :func:`pazufa_corelib.normalization.text.normalize_volltext` as the
first step of its pipeline. The module is named ``html_text`` rather than
``html`` so it cannot be confused with the standard library module of that
name, which ``text.py`` uses to decode entities.

Only :func:`html_to_text` is meant to be called from outside; everything else
is an implementation detail of that conversion.
"""

import re

# --- Element names ------------------------------------------------------------

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

# --- Patterns -----------------------------------------------------------------

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

# --- Conversion ---------------------------------------------------------------


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


def html_to_text(text: str) -> str:
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
