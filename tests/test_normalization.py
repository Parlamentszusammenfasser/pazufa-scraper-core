"""Tests for normalization utilities."""

import hashlib
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from pazufa_corelib.api_model import Autor
from pazufa_corelib.normalization import (
    AuthorIDResolution,
    AuthorResolver,
    NameIDResolution,
    OrganizationIDResolution,
    OrganizationResolver,
    hash_text,
    normalize_name,
    normalize_name_key,
    normalize_volltext,
)
from pazufa_corelib.normalization.experimental import normalize_autor
from pazufa_corelib.normalization.schlagworte import SchlagwortResolver
from pazufa_corelib.normalization.text import (
    _HTML_BLOCK_ELEMENTS,
    _HTML_CELL_ELEMENTS,
    _HTML_ELEMENTS,
    _HTML_ELEMENTS_WITHOUT_TEXT,
    _HTML_INLINE_ELEMENTS,
    _HTML_LINE_ELEMENTS,
    _paragraph_quality_score,
)

# ---------------------------------------------------------------------------
# normalize_volltext
# ---------------------------------------------------------------------------


class TestnormalizeVolltextNfkc:
    def test_fi_ligature_decomposed(self) -> None:
        assert "fi" in normalize_volltext("\ufb01nden")

    def test_ff_ligature_decomposed(self) -> None:
        assert "ff" in normalize_volltext("\ufb00nen")

    def test_superscript_digits(self) -> None:
        # NFKC maps ² → 2
        assert "m2" in normalize_volltext("m\u00b2")

    def test_fullwidth_latin(self) -> None:
        # Ａ (U+FF21) → A
        assert normalize_volltext("\uff21ntrag") == "Antrag"


class TestnormalizeVolltextInvisibleChars:
    def test_soft_hyphen_stripped(self) -> None:
        result = normalize_volltext("Bundes\u00adtag")
        assert "\u00ad" not in result
        assert "Bundestag" in result

    def test_bom_stripped(self) -> None:
        result = normalize_volltext("\ufeffHallo Welt")
        assert "\ufeff" not in result
        assert result == "Hallo Welt"

    def test_zero_width_space_stripped(self) -> None:
        result = normalize_volltext("Hallo\u200bWelt")
        assert "\u200b" not in result
        assert "HalloWelt" in result

    def test_zwj_stripped(self) -> None:
        result = normalize_volltext("Hallo\u200dWelt")
        assert "\u200d" not in result

    def test_zwnj_stripped(self) -> None:
        result = normalize_volltext("Hallo\u200cWelt")
        assert "\u200c" not in result

    def test_multiple_invisible_chars_at_once(self) -> None:
        result = normalize_volltext("\ufeffBundes\u00adtag\u200b Berlin\u200c")
        assert result == "Bundestag Berlin"


class TestnormalizeVolltextC1Controls:
    def test_c1_controls_stripped(self) -> None:
        result = normalize_volltext("Hallo\x85Welt\x96hier")
        assert "\x85" not in result
        assert "\x96" not in result
        assert "HalloWelthier" == result

    def test_all_c1_range_stripped(self) -> None:
        # Every byte from 0x80 to 0x9F should be removed
        c1 = "".join(chr(c) for c in range(0x80, 0xA0))
        result = normalize_volltext(f"A{c1}B")
        assert result == "AB"

    def test_c1_only_string(self) -> None:
        c1_only = "".join(chr(c) for c in range(0x80, 0xA0))
        assert normalize_volltext(c1_only) == ""


class TestnormalizeVolltextC0Controls:
    def test_nul_byte_stripped(self) -> None:
        # NUL (0x00) cannot be stored in a PostgreSQL text column.
        result = normalize_volltext("Hallo\x00Welt")
        assert "\x00" not in result
        assert "HalloWelt" == result

    def test_other_c0_controls_stripped(self) -> None:
        result = normalize_volltext("Hallo\x01Welt\x1fhier\x7fda")
        assert result == "HalloWelthierda"

    def test_all_c0_range_and_del_stripped(self) -> None:
        # Every C0 byte plus DEL is removed, except \t \n \r.
        c0 = "".join(chr(c) for c in range(0x00, 0x20) if c not in (0x09, 0x0A, 0x0D))
        result = normalize_volltext(f"A{c0}\x7fB")
        assert result == "AB"

    def test_tab_newline_cr_preserved(self) -> None:
        # \t \n \r carry layout and must survive (CR is normalized to \n).
        result = normalize_volltext("Eins\tzwei\nDrei\rVier")
        assert result == "Eins\tzwei\nDrei\nVier"


class TestnormalizeVolltextLineEndings:
    def test_crlf_normalized(self) -> None:
        result = normalize_volltext("Zeile eins\r\nZeile zwei\rZeile drei")
        assert "\r" not in result
        assert "Zeile eins\nZeile zwei\nZeile drei" == result

    def test_bare_cr_normalized(self) -> None:
        result = normalize_volltext("Eins\rZwei\rDrei")
        assert "\r" not in result
        assert "Eins\nZwei\nDrei" == result

    def test_mixed_line_endings(self) -> None:
        result = normalize_volltext("Eins\r\nZwei\rDrei\nVier")
        assert result == "Eins\nZwei\nDrei\nVier"


class TestnormalizeVolltextHyphenBreak:
    def test_basic_rejoin(self) -> None:
        result = normalize_volltext("Landes-\nregierung beschlossen")
        assert "Landesregierung" in result

    def test_compound_word_rejoin(self) -> None:
        result = normalize_volltext(
            "Gesetzentwurf zur Änderung des Bundes-\nnaturschutzgesetzes"
        )
        assert "Bundesnaturschutzgesetzes" in result

    def test_hyphen_at_end_of_line_without_continuation(self) -> None:
        # Hyphen followed by blank line (paragraph break) should NOT rejoin
        result = normalize_volltext("Absatz eins-\n\nAbsatz zwei")
        assert "Absatz eins-" in result or "Absatz eins" in result
        assert "Absatz zwei" in result

    def test_hyphen_not_between_word_chars_untouched(self) -> None:
        # Hyphen followed by newline then space should not rejoin
        result = normalize_volltext("Ergebnis: 5-\n 3 Stimmen")
        assert "53" not in result

    def test_hyphen_with_crlf_rejoined(self) -> None:
        # CRLF is normalized to LF first, so the hyphen-break still fires
        result = normalize_volltext("Landes-\r\nregierung")
        assert "Landesregierung" in result

    def test_multiple_hyphen_breaks(self) -> None:
        text = "Bundes-\nregierung und Landes-\nparlament"
        result = normalize_volltext(text)
        assert "Bundesregierung" in result
        assert "Landesparlament" in result


class TestnormalizeVolltextMultiSpace:
    def test_double_spaces_collapsed(self) -> None:
        result = normalize_volltext("Der  Landtag   von   Baden-Württemberg")
        assert "  " not in result
        assert "Der Landtag von Baden-Württemberg" in result

    def test_tabs_collapsed(self) -> None:
        result = normalize_volltext("Spalte\t\tZwei")
        assert "\t" not in result
        assert "Spalte Zwei" in result

    def test_mixed_spaces_and_tabs(self) -> None:
        result = normalize_volltext("A \t B")
        assert result == "A B"

    def test_single_space_preserved(self) -> None:
        result = normalize_volltext("Hallo Welt")
        assert result == "Hallo Welt"

    def test_newlines_not_collapsed(self) -> None:
        # Paragraph-separating blank lines must survive
        text = "Absatz eins.\n\nAbsatz zwei."
        result = normalize_volltext(text)
        assert "\n\n" in result


class TestnormalizeVolltextParagraphQuality:
    def test_garbled_paragraph_removed(self) -> None:
        clean = "Dies ist ein normaler deutscher Absatz mit korrektem Text."
        garbled = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        text = f"{clean}\n\n{garbled}"
        result = normalize_volltext(text)
        assert clean in result
        assert garbled not in result

    def test_mixed_quality_paragraphs(self) -> None:
        clean = "Die Landesregierung wird aufgefordert zu berichten."
        garbled = "ĚĞƌ&ƌĂŬƚŝŽŶ ǁćŚƌůĞŝƐƚƵŶŐ ŝƚĞůůƚ"
        text = f"{clean}\n\n{garbled}"
        result = normalize_volltext(text)
        assert clean in result
        assert "ĚĞƌ" not in result

    def test_multiple_clean_paragraphs_preserved(self) -> None:
        p1 = "Der Landtag hat in seiner heutigen Sitzung beschlossen."
        p2 = "Die Landesregierung wird aufgefordert zu berichten."
        result = normalize_volltext(f"{p1}\n\n{p2}")
        assert p1 in result
        assert p2 in result
        assert "\n\n" in result

    def test_all_garbled_paragraphs_removed(self) -> None:
        g1 = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        g2 = "\u018a\u018b\u018c\u018d\u018e\u018f\u0190\u0191\u0192\u0193"
        result = normalize_volltext(f"{g1}\n\n{g2}")
        assert result == ""

    def test_short_paragraph_all_caps_kept(self) -> None:
        text = "EINLEITUNG\n\nDie Landesregierung wird aufgefordert zu berichten."
        result = normalize_volltext(text)
        assert "EINLEITUNG" in result


class TestnormalizeVolltextAngleBrackets:
    def test_angle_brackets_replaced(self) -> None:
        result = normalize_volltext("<poststelle@lfdi.bwl.de>")
        assert "<" not in result
        assert ">" not in result
        assert "\u2039poststelle@lfdi.bwl.de\u203a" == result

    def test_nested_angle_brackets(self) -> None:
        result = normalize_volltext("a < b > c")
        assert "<" not in result
        assert ">" not in result
        assert "\u2039" in result
        assert "\u203a" in result

    def test_no_angle_brackets_unchanged(self) -> None:
        text = "Normaler Text ohne Klammern"
        assert normalize_volltext(text) == text


class TestnormalizeVolltextEdgeCases:
    def test_empty_string(self) -> None:
        assert normalize_volltext("") == ""

    def test_whitespace_only(self) -> None:
        assert normalize_volltext("   \n\n   ") == ""

    def test_clean_text_unchanged(self) -> None:
        text = "Der Landtag von Baden-Württemberg hat beschlossen."
        assert normalize_volltext(text) == text

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert normalize_volltext("  Hallo Welt  ") == "Hallo Welt"

    def test_idempotent(self) -> None:
        # Applying normalisation twice should give the same result
        text = "Landes-\nregierung  hat\x85 beschlossen\r\n"
        once = normalize_volltext(text)
        twice = normalize_volltext(once)
        assert once == twice

    def test_full_pipeline_combined(self) -> None:
        # Exercises all steps at once: NFKC + invisible + C1 + CRLF +
        # hyphen-break + multi-space + garbled removal + angle brackets
        garbled = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        text = (
            "\ufeffDer  Landtag\x85 hat die Landes-\r\nregierung <aufgefordert>"
            f"\n\n{garbled}"
        )
        result = normalize_volltext(text)
        assert "\ufeff" not in result
        assert "\x85" not in result
        assert "\r" not in result
        assert "  " not in result
        assert "Landesregierung" in result
        assert "\u2039aufgefordert\u203a" in result
        assert garbled not in result

    def test_unicode_letters_in_hyphen_break(self) -> None:
        # German umlauts should be treated as word characters by \w
        result = normalize_volltext("Über-\ngangsregelung")
        assert "Übergangsregelung" in result


# ---------------------------------------------------------------------------
# normalize_volltext — HTML entities
#
# Entity decoding applies to every input, with or without markup.
# ---------------------------------------------------------------------------


class TestnormalizeVolltextEntities:
    def test_plain_text_unaffected_by_unescape(self) -> None:
        # html.unescape() is a no-op on text with no entity sequences.
        text = "Der Landtag von Baden-Württemberg hat beschlossen."
        assert normalize_volltext(text) == text

    def test_html_named_entities_decoded(self) -> None:
        result = normalize_volltext("Titel &amp; Inhalt &uuml;ber alles")
        assert "&amp;" not in result
        assert "&uuml;" not in result
        assert "Titel & Inhalt über alles" == result

    def test_nbsp_entity_decoded_to_space(self) -> None:
        # &nbsp; → U+00A0, then NFKC collapses it to a regular space.
        result = normalize_volltext("Wort&nbsp;Wort")
        assert "&nbsp;" not in result
        assert "Wort Wort" == result

    def test_numeric_html_entity_decoded(self) -> None:
        # &#160; → U+00A0, then NFKC collapses it to a regular space.
        result = normalize_volltext("Wort&#160;Wort")
        assert "&#160;" not in result
        assert "Wort Wort" == result


# ---------------------------------------------------------------------------
# normalize_volltext — HTML markup
# ---------------------------------------------------------------------------


class TestnormalizeVolltextHtml:
    def test_block_elements_become_paragraphs(self) -> None:
        result = normalize_volltext("<p>Absatz eins</p><p>Absatz zwei</p>")
        assert result == "Absatz eins\n\nAbsatz zwei"

    def test_unclosed_paragraphs_become_paragraphs(self) -> None:
        result = normalize_volltext("<p>eins<p>zwei<p>drei")
        assert result == "eins\n\nzwei\n\ndrei"

    def test_br_becomes_line_break(self) -> None:
        result = normalize_volltext("Zeile eins<br>Zeile zwei<br/>Zeile drei")
        assert result == "Zeile eins\nZeile zwei\nZeile drei"

    def test_inline_tags_removed_without_gap(self) -> None:
        result = normalize_volltext("Landes<span>regierung</span> und <b>Land</b>tag")
        assert result == "Landesregierung und Landtag"

    def test_list_items_become_lines(self) -> None:
        result = normalize_volltext(
            "<ul><li>zu berichten,</li><li>vorzulegen.</li></ul>"
        )
        assert result == "zu berichten,\nvorzulegen."

    def test_table_rows_become_lines_and_cells_spaces(self) -> None:
        markup = (
            "<table><tr><th>Drucksache</th><th>Titel</th></tr>"
            "<tr><td>17/1234</td><td>Antrag der Fraktion</td></tr></table>"
        )
        result = normalize_volltext(markup)
        assert result == "Drucksache Titel\n17/1234 Antrag der Fraktion"

    def test_uppercase_tags_and_unquoted_attributes(self) -> None:
        markup = (
            '<P ALIGN=CENTER><FONT FACE="Arial">Der Landtag hat beschlossen</FONT></P>'
        )
        assert normalize_volltext(markup) == "Der Landtag hat beschlossen"

    def test_quoted_attribute_may_contain_gt(self) -> None:
        markup = '<p><a title="a > b" href="/x?a=1&amp;sect=3">Link</a></p>'
        assert normalize_volltext(markup) == "Link"

    def test_script_style_and_comments_removed_with_content(self) -> None:
        markup = (
            "<style>p{color:red}</style><!-- Navigation -->"
            '<script>var s = "</div>"; if (a<b) track()</script><p>Text</p>'
        )
        assert normalize_volltext(markup) == "Text"

    def test_first_opened_construct_wins(self) -> None:
        # "<!--" inside a script is script content, not the start of a comment
        markup = "<script>if (a <!--b) x()</script><p>Text</p><!-- Kommentar -->"
        assert normalize_volltext(markup) == "Text"

    def test_unclosed_comment_kept_as_text(self) -> None:
        markup = "<p>Text</p><!-- offen <p>Rest</p>"
        result = normalize_volltext(markup)
        assert result == "Text\n\n‹!-- offen\n\nRest"

    def test_svg_removed_with_content(self) -> None:
        markup = "<svg><title>Icon</title><text>Grafik</text></svg><p>Text</p>"
        assert normalize_volltext(markup) == "Text"

    def test_doctype_head_and_source_whitespace(self) -> None:
        markup = (
            "<!DOCTYPE html>\n<html>\n  <head>\n    <title>Plenarprotokoll</title>\n"
            "  </head>\n\n  <body>\n    <p>Der  Landtag\n    tagt.</p>\n  </body>\n</html>"
        )
        assert normalize_volltext(markup) == "Der Landtag tagt."

    def test_unclosed_head_ends_at_body(self) -> None:
        markup = "<html><head><title>Titel</title><body><p>Inhalt</p></body></html>"
        assert normalize_volltext(markup) == "Inhalt"

    def test_word_markup_removed(self) -> None:
        markup = (
            "<!--[if gte mso 9]><xml><w:WordDocument></w:WordDocument></xml>"
            "<![endif]--><p class=MsoNormal><![if !supportLists]>1.<![endif]>"
            " Der Landtag<o:p></o:p></p><st1:place>Stuttgart</st1:place>"
        )
        result = normalize_volltext(markup)
        assert result == "1. Der Landtag\n\nStuttgart"

    def test_custom_elements_removed(self) -> None:
        markup = "<my-widget>Inhalt</my-widget>"
        assert normalize_volltext(markup) == "Inhalt"

    def test_cdata_removed(self) -> None:
        markup = "<p>A<![CDATA[ x < y ]]>B</p>"
        assert normalize_volltext(markup) == "AB"

    def test_element_roles_do_not_overlap(self) -> None:
        roles = [
            _HTML_BLOCK_ELEMENTS,
            _HTML_LINE_ELEMENTS,
            _HTML_CELL_ELEMENTS,
            _HTML_ELEMENTS_WITHOUT_TEXT,
            frozenset({"head"}),
            _HTML_INLINE_ELEMENTS,
        ]
        assert sum(len(role) for role in roles) == len(_HTML_ELEMENTS)

    def test_unclosed_element_without_text_is_a_tag(self) -> None:
        # Without </math> nothing is removed with its content, but <math> is
        # still a tag and must not leak into the text.
        markup = "<p>Formel <math>x</p>"
        assert normalize_volltext(markup) == "Formel x"

    def test_escaped_markup_stays_text(self) -> None:
        markup = "<p>Das Element &lt;b&gt; macht Text fett.</p>"
        result = normalize_volltext(markup)
        assert result == "Das Element ‹b› macht Text fett."

    def test_entities_decoded_once(self) -> None:
        markup = "<p>Ma&szlig;nahmen &amp;lt;b&amp;gt;</p>"
        result = normalize_volltext(markup)
        assert result == "Maßnahmen &lt;b&gt;"

    def test_angle_brackets_that_are_not_tags_kept(self) -> None:
        markup = "<p>Kontakt: <poststelle@lfdi.bwl.de>, Wert <5, a < b</p>"
        result = normalize_volltext(markup)
        assert result == "Kontakt: ‹poststelle@lfdi.bwl.de›, Wert ‹5, a ‹ b"


# ---------------------------------------------------------------------------
# normalize_volltext — line-end hyphens
# ---------------------------------------------------------------------------


class TestnormalizeVolltextDehyphenation:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # syllable breaks are joined
            ("Landes-\nregierung", "Landesregierung"),
            ("Über-\ngangsregelung", "Übergangsregelung"),
            ("Ge-\nsetzentwurf", "Gesetzentwurf"),
            ("BESCHLUSS-\nEMPFEHLUNG", "BESCHLUSSEMPFEHLUNG"),
            # real hyphens before a capitalised word stay
            ("Baden-\nWürttemberg", "Baden-Württemberg"),
            ("CDU-\nFraktion", "CDU-Fraktion"),
            ("E-\nMail", "E-Mail"),
            ("Kfz-\nSteuer", "Kfz-Steuer"),
            ("Bund-Länder-\nArbeitsgruppe", "Bund-Länder-Arbeitsgruppe"),
            # real hyphens next to a digit stay
            ("20-\njährige", "20-jährige"),
            ("Covid-\n19-Pandemie", "Covid-19-Pandemie"),
            # suspended hyphens stay, the line break becomes a space
            ("Bundes-\nund Landesmittel", "Bundes- und Landesmittel"),
            ("Hin-\noder Rückfahrt", "Hin- oder Rückfahrt"),
        ],
    )
    def test_line_end_hyphen(self, text: str, expected: str) -> None:
        result = normalize_volltext(text)
        assert result == expected
        # hash_text normalizes again with the defaults; that must not change it
        assert normalize_volltext(result) == result

    def test_hash_text_matches_stored_text(self) -> None:
        markup = "<p>Baden-<br>Württemberg, Bundes-<br>und Landes-<br>mittel</p>"
        volltext = normalize_volltext(markup)
        assert volltext == "Baden-Württemberg, Bundes- und Landesmittel"
        expected = hashlib.sha256(volltext.encode("utf-8")).hexdigest()
        assert hash_text(volltext)[0] == expected

    def test_word_broken_over_three_lines(self) -> None:
        text = "Grundstücksverkehrs-\ngenehmigungs-\nverordnung"
        result = normalize_volltext(text)
        assert result == "Grundstücksverkehrsgenehmigungsverordnung"

    def test_crlf_line_end(self) -> None:
        text = "Landes-\r\nregierung in Baden-\r\nWürttemberg"
        result = normalize_volltext(text)
        assert result == "Landesregierung in Baden-Württemberg"

    def test_lowercase_compound_still_joined(self) -> None:
        # Known limitation: a lowercase continuation looks like a syllable break
        text = "deutsch-\nfranzösische"
        assert normalize_volltext(text) == ("deutschfranzösische")

    def test_soft_hyphen_at_line_end_joined(self) -> None:
        for text in ("Landes­\nregierung", "Landes&shy;\r\nregierung"):
            result = normalize_volltext(text)
            assert result == "Landesregierung"

    def test_typographic_hyphens_at_line_end(self) -> None:
        # U+2010 hyphen; U+2011 non-breaking hyphen becomes U+2010 under NFKC
        for hyphen in ("‐", "‑"):
            text = f"Landes{hyphen}\nregierung in Baden{hyphen}\nWürttemberg"
            result = normalize_volltext(text)
            assert result == "Landesregierung in Baden‐Württemberg"

    def test_line_end_hyphen_from_br_tag(self) -> None:
        markup = "<p>Das Land Baden-<br>Württemberg und die Landes-<br>regierung</p>"
        result = normalize_volltext(markup)
        assert result == "Das Land Baden-Württemberg und die Landesregierung"


# ---------------------------------------------------------------------------
# _paragraph_quality_score
# ---------------------------------------------------------------------------


class TestParagraphQualityScore:
    def test_clean_german_text(self) -> None:
        text = "Der Landtag von Baden-Württemberg hat in seiner Sitzung beschlossen."
        assert _paragraph_quality_score(text) >= 0.8

    def test_c1_heavy_text(self) -> None:
        text = "Hallo\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d"
        assert _paragraph_quality_score(text) < 0.5

    def test_latin_ext_b_heavy(self) -> None:
        text = "\u0180\u0181\u0182\u0183\u0184abc"
        assert _paragraph_quality_score(text) < 0.5

    def test_vowelless_words(self) -> None:
        text = "bxcdf ghklm nprst vwxyz qwrty"
        assert _paragraph_quality_score(text) < 0.5

    def test_excessive_uppercase(self) -> None:
        text = "ABCDEFGHIJ KLMNOPQRST UVWXYZ ABCDE"
        assert _paragraph_quality_score(text) < 0.5

    def test_empty_paragraph(self) -> None:
        assert _paragraph_quality_score("") == 1.0

    def test_whitespace_only(self) -> None:
        assert _paragraph_quality_score("   ") == 1.0

    def test_short_all_caps_heading(self) -> None:
        assert _paragraph_quality_score("EINLEITUNG") == 1.0

    def test_short_vowelless_heading(self) -> None:
        assert _paragraph_quality_score("§ 3") == 1.0

    def test_score_clamped_to_zero(self) -> None:
        # All four penalties hit hard → score should be 0.0, not negative
        text = "\x80\x81\x82\u0180\u0181BXCDF GHKLM NPRST VWXYZ QWRTY"
        assert _paragraph_quality_score(text) == 0.0

    def test_score_always_between_0_and_1(self) -> None:
        samples = [
            "Normaler deutscher Text mit Umlauten äöü.",
            "\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ ABCDE FGHIJ KLMNO",
            "bxcdf ghklm nprst vwxyz qwrty abcdf",
            "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187",
            "",
            "A",
            "§ 1 Zuständigkeit",
        ]
        for sample in samples:
            score = _paragraph_quality_score(sample)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for: {sample!r}"

    def test_three_word_all_caps_exempt(self) -> None:
        # 3 words → short paragraph → uppercase penalty skipped
        assert _paragraph_quality_score("TEIL ZWEI ENDE") >= 0.8

    def test_four_word_all_caps_penalised(self) -> None:
        # 4 words → uppercase penalty applies
        assert _paragraph_quality_score("TEIL ZWEI DREI ENDE") < 0.5

    def test_no_alpha_chars(self) -> None:
        # Paragraph with only digits/symbols → no division by zero
        score = _paragraph_quality_score("123 456 789")
        assert 0.0 <= score <= 1.0

    def test_long_clean_german_paragraph(self) -> None:
        text = (
            "Die Landesregierung wird aufgefordert, dem Landtag über den "
            "aktuellen Stand der Umsetzung des Klimaschutzgesetzes zu berichten. "
            "Dabei sollen insbesondere die Fortschritte im Bereich der "
            "erneuerbaren Energien und der Gebäudesanierung dargestellt werden."
        )
        assert _paragraph_quality_score(text) >= 0.9

    def test_mixed_case_normal_text(self) -> None:
        # Normal capitalization (first word, proper nouns) should score well
        text = "Der Ministerpräsident Kretschmann hat die Sitzung eröffnet."
        assert _paragraph_quality_score(text) >= 0.8


# ---------------------------------------------------------------------------
# AuthorResolver
# ---------------------------------------------------------------------------


class TestAuthorResolver:
    @pytest.fixture(scope="class")
    def resolver(self) -> AuthorResolver:
        return AuthorResolver()

    # --- constructor -------------------------------------------------------

    def test_empty_files_raises(self) -> None:
        with pytest.raises(ValueError, match="No vocabulary files"):
            AuthorResolver(files=[])

    def test_wrong_file_type_raises(self, tmp_path: Path) -> None:
        org_yaml = tmp_path / "orgs.yaml"
        org_yaml.write_text(
            "names:\n"
            "  - id: some-org\n"
            "    canonical_name: Some Org\n"
            "    acronym: SO\n"
            "    aliases: []\n"
        )
        with pytest.raises(ValueError):
            AuthorResolver(files=[org_yaml])

    def test_custom_match_threshold_stored(self) -> None:
        assert (
            AuthorResolver(match_threshold=95.0).explain("Olaf Scholz")["threshold"]
            == 95.0
        )

    def test_custom_near_tie_epsilon_stored(self) -> None:
        assert (
            AuthorResolver(near_tie_epsilon=5.0).explain("Olaf Scholz")[
                "near_tie_epsilon"
            ]
            == 5.0
        )

    def test_init_emits_debug_log(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.authors"
        ):
            AuthorResolver()
        assert any("AuthorResolver initialised" in r.message for r in caplog.records)

    # --- resolve: exact matches -------------------------------------------

    def test_exact_canonical_name(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Olaf Scholz")
        assert r.resolved_id == "scholz-olaf"
        assert r.score == 100.0
        assert r.matched

    def test_exact_alias_comma_form(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Scholz, Olaf")
        assert r.resolved_id == "scholz-olaf"
        assert r.score == 100.0

    def test_honorific_stripped_before_resolve(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Dr. Angela Merkel")
        assert r.resolved_id == "merkel-angela"
        assert r.matched

    def test_umlaut_variant_exact(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Schroeder, Gerhard")
        assert r.resolved_id == "schroeder-gerhard"
        assert r.matched

    def test_von_particle(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Richard von Weizsäcker")
        assert r.resolved_id == "von-weizsaecker-richard"
        assert r.matched

    def test_von_umlaut_comma_form(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("von Weizsaecker, Richard")
        assert r.resolved_id == "von-weizsaecker-richard"
        assert r.matched

    # --- resolve: fuzzy matches -------------------------------------------

    def test_fuzzy_typo(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Helmut Schmitt")
        assert r.resolved_id == "schmidt-helmut"
        assert r.matched

    def test_high_threshold_rejects_fuzzy(self) -> None:
        assert (
            not AuthorResolver(match_threshold=100.0).resolve("Helmut Schmitt").matched
        )

    def test_default_threshold_accepts_fuzzy(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Helmut Schmitt")
        assert r.matched
        assert r.resolved_id == "schmidt-helmut"

    # --- resolve: unresolved cases ----------------------------------------

    def test_unknown_name_unresolved(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Max Mustermann")
        assert not r.matched
        assert r.score == 0.0
        assert r.resolved_id == ""
        assert not r.changed

    def test_empty_query_unresolved(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("")
        assert not r.matched
        assert r.score == 0.0

    def test_honorific_only_unresolved(self, resolver: AuthorResolver) -> None:
        assert not resolver.resolve("Dr.").matched

    def test_empty_resolver_returns_unresolved(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("names: []\n")
        r = AuthorResolver(files=[empty]).resolve("Olaf Scholz")
        assert not r.matched
        assert r.score == 0.0

    # --- matched / changed flags ------------------------------------------

    def test_changed_true_on_alias(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Scholz, Olaf")
        assert r.matched and r.changed

    def test_changed_true_on_honorific(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Dr. Merkel")
        assert r.matched and r.changed

    def test_changed_false_on_canonical(self, resolver: AuthorResolver) -> None:
        r = resolver.resolve("Olaf Scholz")
        assert r.matched and not r.changed

    def test_changed_false_on_no_match(self, resolver: AuthorResolver) -> None:
        assert not resolver.resolve("Unbekannt Jemand").changed

    # --- resolve_batch ----------------------------------------------------

    def test_resolve_batch_order_preserved(self, resolver: AuthorResolver) -> None:
        results = resolver.resolve_batch(
            ["Olaf Scholz", "Angela Merkel", "Max Mustermann"]
        )
        assert results[0].resolved_id == "scholz-olaf"
        assert results[1].resolved_id == "merkel-angela"
        assert not results[2].matched

    def test_resolve_batch_empty_list(self, resolver: AuthorResolver) -> None:
        assert resolver.resolve_batch([]) == []

    def test_resolve_batch_consistent_with_single(
        self, resolver: AuthorResolver
    ) -> None:
        names = ["Olaf Scholz", "Angela Merkel", "Helmut Schmidt"]
        batch = resolver.resolve_batch(names)
        singles = [resolver.resolve(n) for n in names]
        assert [r.resolved_id for r in batch] == [r.resolved_id for r in singles]
        assert [r.score for r in batch] == [r.score for r in singles]

    # --- check_author -----------------------------------------------------

    def test_check_author_canonical(self, resolver: AuthorResolver) -> None:
        assert resolver.check_author("Olaf Scholz") is True

    def test_check_author_comma_form(self, resolver: AuthorResolver) -> None:
        assert resolver.check_author("Scholz, Olaf") is True

    def test_check_author_alias(self, resolver: AuthorResolver) -> None:
        assert resolver.check_author("Brandt") is True

    def test_check_author_honorific(self, resolver: AuthorResolver) -> None:
        assert resolver.check_author("Dr. Angela Merkel") is True

    def test_check_author_unknown(self, resolver: AuthorResolver) -> None:
        assert resolver.check_author("Max Mustermann") is False

    # --- fuzzy_check_author -----------------------------------------------

    def test_fuzzy_check_author_typo(self, resolver: AuthorResolver) -> None:
        assert resolver.fuzzy_check_author("Helmut Schmitt") is True

    def test_fuzzy_check_author_unknown(self, resolver: AuthorResolver) -> None:
        assert resolver.fuzzy_check_author("Max Mustermann") is False

    def test_fuzzy_check_author_debug_log(
        self, resolver: AuthorResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.authors"
        ):
            resolver.fuzzy_check_author("Helmut Schmitt")
        assert any("Fuzzy author check" in r.message for r in caplog.records)

    # --- get_author_by_id ------------------------------------------------

    def test_get_author_by_id_hit(self, resolver: AuthorResolver) -> None:
        author = resolver.get_author_by_id("scholz-olaf")
        assert author is not None
        assert author.id == "scholz-olaf"
        assert author.canonical_name == "Olaf Scholz"

    def test_get_author_by_id_miss(self, resolver: AuthorResolver) -> None:
        assert resolver.get_author_by_id("does-not-exist") is None

    # --- canonicalize_author ---------------------------------------------

    def test_canonicalize_author_resolved(self, resolver: AuthorResolver) -> None:
        assert resolver.canonicalize_author("Olaf Scholz") == "Olaf Scholz"

    def test_canonicalize_author_honorific(self, resolver: AuthorResolver) -> None:
        assert resolver.canonicalize_author("Dr. Angela Merkel") == "Angela Merkel"

    def test_canonicalize_author_unresolved_non_strict(
        self, resolver: AuthorResolver
    ) -> None:
        assert resolver.canonicalize_author("Max Mustermann") == "Max Mustermann"

    def test_canonicalize_author_unresolved_strict(
        self, resolver: AuthorResolver
    ) -> None:
        assert resolver.canonicalize_author("Max Mustermann", strict=True) is None

    def test_canonicalize_author_debug_log_resolved(
        self, resolver: AuthorResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.authors"
        ):
            resolver.canonicalize_author("Olaf Scholz")
        assert any("Resolved author" in r.message for r in caplog.records)

    def test_canonicalize_author_debug_log_unresolved(
        self, resolver: AuthorResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.authors"
        ):
            resolver.canonicalize_author("Max Mustermann")
        assert any("unresolved, keeping original" in r.message for r in caplog.records)

    # --- canonicalize_authors --------------------------------------------

    def test_canonicalize_authors_basic(self, resolver: AuthorResolver) -> None:
        assert resolver.canonicalize_authors(["Olaf Scholz", "Angela Merkel"]) == [
            "Olaf Scholz",
            "Angela Merkel",
        ]

    def test_canonicalize_authors_unmatched_kept(
        self, resolver: AuthorResolver
    ) -> None:
        result = resolver.canonicalize_authors(["Olaf Scholz", "Max Mustermann"])
        assert result == ["Olaf Scholz", "Max Mustermann"]

    def test_canonicalize_authors_strict_sets_none(
        self, resolver: AuthorResolver
    ) -> None:
        assert resolver.canonicalize_authors(
            ["Olaf Scholz", "Max Mustermann"], strict=True
        ) == ["Olaf Scholz", None]

    def test_canonicalize_authors_empty_list(self, resolver: AuthorResolver) -> None:
        assert resolver.canonicalize_authors([]) == []

    # --- explain ---------------------------------------------------------

    def test_explain_exact_hit(self, resolver: AuthorResolver) -> None:
        trace = resolver.explain("Olaf Scholz")
        assert trace["query"] == "Olaf Scholz"
        assert trace["exact_hit"] is True
        assert len(trace["top_k"]) == 1
        assert trace["top_k"][0]["id"] == "scholz-olaf"
        assert trace["top_k"][0]["score"] == 100.0

    def test_explain_fuzzy_ranks_candidates(self, resolver: AuthorResolver) -> None:
        trace = resolver.explain("Helmut Schmitt", k=3)
        assert trace["exact_hit"] is False
        assert len(trace["top_k"]) == 3
        assert trace["top_k"][0]["id"] == "schmidt-helmut"
        scores = [c["score"] for c in trace["top_k"]]
        assert scores == sorted(scores, reverse=True)

    def test_explain_empty_query(self, resolver: AuthorResolver) -> None:
        trace = resolver.explain("")
        assert trace["normalized_key"] == ""
        assert trace["exact_hit"] is False
        assert trace["top_k"] == []

    def test_explain_thresholds_match_defaults(self, resolver: AuthorResolver) -> None:
        trace = resolver.explain("Olaf Scholz")
        assert trace["threshold"] == 90.0
        assert trace["near_tie_epsilon"] == 1.0

    def test_explain_k_caps_results(self, resolver: AuthorResolver) -> None:
        assert len(resolver.explain("Helmut Schmitt", k=2)["top_k"]) == 2

    def test_explain_empty_resolver(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("names: []\n")
        trace = AuthorResolver(files=[empty]).explain("Olaf Scholz")
        assert trace["top_k"] == []
        assert trace["exact_hit"] is False


# ---------------------------------------------------------------------------
# OrganisationResolver
# ---------------------------------------------------------------------------


class TestOrganisationResolver:
    @pytest.fixture(scope="class")
    def resolver(self) -> OrganizationResolver:
        return OrganizationResolver()

    # --- constructor -------------------------------------------------------

    def test_empty_files_raises(self) -> None:
        with pytest.raises(ValueError, match="No vocabulary files"):
            OrganizationResolver(files=[])

    def test_wrong_file_type_raises(self, tmp_path: Path) -> None:
        author_yaml = tmp_path / "authors.yaml"
        author_yaml.write_text(
            "names:\n"
            "  - id: some-person\n"
            "    canonical_name: Some Person\n"
            "    aliases: []\n"
        )
        with pytest.raises(ValueError):
            OrganizationResolver(files=[author_yaml])

    def test_custom_match_threshold_stored(self) -> None:
        assert (
            OrganizationResolver(match_threshold=42.0).explain("SPD")["threshold"]
            == 42.0
        )

    def test_custom_near_tie_epsilon_stored(self) -> None:
        assert (
            OrganizationResolver(near_tie_epsilon=10.0).explain("SPD")[
                "near_tie_epsilon"
            ]
            == 10.0
        )

    def test_init_emits_debug_log(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.organizations"
        ):
            OrganizationResolver()
        assert any(
            "OrganizationResolver initialised" in r.message for r in caplog.records
        )

    # --- resolve: exact matches -------------------------------------------

    def test_exact_canonical_name(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("SPD")
        assert r.resolved_id == "spd"
        assert r.score == 100.0
        assert r.matched

    def test_exact_full_name_alias(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("Sozialdemokratische Partei Deutschlands")
        assert r.resolved_id == "spd"
        assert r.score == 100.0

    def test_exact_via_slash_normalisation(
        self, resolver: OrganizationResolver
    ) -> None:
        r = resolver.resolve("Bündnis 90 Die Grünen")
        assert r.resolved_id == "gruene"
        assert r.score == 100.0

    # --- CDU/CSU three-way split ------------------------------------------

    def test_cdu_csu_canonical(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("CDU/CSU")
        assert r.resolved_id == "cdu-csu"
        assert r.score == 100.0
        assert r.acronym == "CDU/CSU"

    def test_cdu_csu_alias_unionsparteien(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("Unionsparteien")
        assert r.resolved_id == "cdu-csu"
        assert r.matched
        assert r.changed

    def test_cdu_resolves_to_cdu_not_cdu_csu(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.resolve("CDU").resolved_id == "cdu"

    def test_csu_resolves_to_csu_not_cdu_csu(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.resolve("CSU").resolved_id == "csu"

    # --- resolve: fuzzy matches -------------------------------------------

    def test_fuzzy_cosine_variant(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("Sozialdemokratische Partei")
        assert r.resolved_id == "spd"
        assert r.matched

    def test_umlaut_variant(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("Alternative fuer Deutschland")
        assert r.resolved_id == "afd"
        assert r.matched

    def test_high_threshold_rejects_borderline(self) -> None:
        default = OrganizationResolver().resolve("Sozialdemokratische Partei")
        assert default.matched
        strict = OrganizationResolver(match_threshold=default.score + 1.0).resolve(
            "Sozialdemokratische Partei"
        )
        assert not strict.matched
        assert strict.score == 0.0

    # --- resolve: unresolved cases ----------------------------------------

    def test_unknown_name_unresolved(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("Bundeswehr")
        assert not r.matched
        assert r.score == 0.0
        assert r.resolved_id == ""

    def test_empty_query_unresolved(self, resolver: OrganizationResolver) -> None:
        assert not resolver.resolve("").matched

    def test_empty_resolver_returns_unresolved(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("names: []\n")
        assert not OrganizationResolver(files=[empty]).resolve("SPD").matched

    # --- matched / changed flags ------------------------------------------

    def test_changed_true_on_alias(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("Unionsparteien")
        assert r.matched and r.changed

    def test_changed_false_on_canonical(self, resolver: OrganizationResolver) -> None:
        r = resolver.resolve("SPD")
        assert r.matched and not r.changed

    def test_changed_false_on_no_match(self, resolver: OrganizationResolver) -> None:
        assert not resolver.resolve("Piratenpartei").changed

    # --- acronym on resolution result -------------------------------------

    def test_acronym_on_matched(self, resolver: OrganizationResolver) -> None:
        assert (
            resolver.resolve("Sozialdemokratische Partei Deutschlands").acronym == "SPD"
        )

    def test_acronym_none_on_unresolved(self, resolver: OrganizationResolver) -> None:
        assert resolver.resolve("Piratenpartei").acronym is None

    def test_acronym_none_for_org_without_acronym(self, tmp_path: Path) -> None:
        org_yaml = tmp_path / "orgs.yaml"
        org_yaml.write_text(
            "names:\n"
            "  - id: no-acronym-org\n"
            "    canonical_name: Organisation Ohne Kuerzel\n"
            "    acronym:\n"
            "    aliases: []\n"
        )
        r = OrganizationResolver(files=[org_yaml]).resolve("Organisation Ohne Kuerzel")
        assert r.matched
        assert r.acronym is None

    # --- resolve_batch ----------------------------------------------------

    def test_resolve_batch_basic(self, resolver: OrganizationResolver) -> None:
        results = resolver.resolve_batch(["CDU", "SPD", "FDP"])
        assert [r.resolved_id for r in results] == ["cdu", "spd", "fdp"]

    def test_resolve_batch_order_preserved(
        self, resolver: OrganizationResolver
    ) -> None:
        queries = ["CDU/CSU", "Die Linke", "Freie Wähler"]
        results = resolver.resolve_batch(queries)
        assert results[0].resolved_id == "cdu-csu"
        assert results[1].resolved_id == "linke"
        assert results[2].resolved_id == "fw"

    def test_resolve_batch_mixed_match(self, resolver: OrganizationResolver) -> None:
        results = resolver.resolve_batch(["SPD", "Bundeswehr"])
        assert results[0].matched
        assert not results[1].matched

    def test_resolve_batch_includes_acronym(
        self, resolver: OrganizationResolver
    ) -> None:
        results = resolver.resolve_batch(["CDU", "FDP"])
        assert results[0].acronym == "CDU"
        assert results[1].acronym == "FDP"

    def test_resolve_batch_empty_list(self, resolver: OrganizationResolver) -> None:
        assert resolver.resolve_batch([]) == []

    def test_resolve_batch_empty_resolver(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("names: []\n")
        results = OrganizationResolver(files=[empty]).resolve_batch(["SPD"])
        assert not results[0].matched
        assert results[0].score == 0.0

    def test_resolve_batch_near_tie_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        near_tie_yaml = tmp_path / "near_tie.yaml"
        near_tie_yaml.write_text(
            "names:\n"
            "  - id: org-alpha\n"
            "    canonical_name: Deutsche Organisation Test Alpha\n"
            "    acronym: null\n"
            "    aliases: []\n"
            "  - id: org-beta\n"
            "    canonical_name: Deutsche Organisation Test Beta\n"
            "    acronym: null\n"
            "    aliases: []\n"
        )
        resolver = OrganizationResolver(files=[near_tie_yaml])
        with caplog.at_level(
            logging.WARNING, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.resolve_batch(["Deutsche Organisation Test"])
        assert any("Near-tie" in r.message for r in caplog.records)

    def test_near_tie_epsilon_zero_suppresses_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        near_tie_yaml = tmp_path / "near_tie.yaml"
        near_tie_yaml.write_text(
            "names:\n"
            "  - id: org-alpha\n"
            "    canonical_name: Deutsche Organisation Test Alpha\n"
            "    acronym: null\n"
            "    aliases: []\n"
            "  - id: org-beta\n"
            "    canonical_name: Deutsche Organisation Test Beta\n"
            "    acronym: null\n"
            "    aliases: []\n"
        )
        resolver = OrganizationResolver(files=[near_tie_yaml], near_tie_epsilon=0.0)
        with caplog.at_level(
            logging.WARNING, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.resolve_batch(["Deutsche Organisation Test"])
        assert not any("Near-tie" in r.message for r in caplog.records)

    # --- check_organization -----------------------------------------------

    def test_check_organization_canonical(self, resolver: OrganizationResolver) -> None:
        assert (
            resolver.check_organization("Sozialdemokratische Partei Deutschlands")
            is True
        )

    def test_check_organization_alias(self, resolver: OrganizationResolver) -> None:
        assert resolver.check_organization("SPD") is True

    def test_check_organization_miss(self, resolver: OrganizationResolver) -> None:
        assert resolver.check_organization("Piratenpartei") is False

    # --- fuzzy_check_organization -----------------------------------------

    def test_fuzzy_check_organization_hit(self, resolver: OrganizationResolver) -> None:
        assert resolver.fuzzy_check_organization("Sozialdemokratische Partei") is True

    def test_fuzzy_check_organization_exact(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.fuzzy_check_organization("SPD") is True

    def test_fuzzy_check_organization_miss(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.fuzzy_check_organization("Bundeswehr") is False

    def test_fuzzy_check_organization_debug_log(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.fuzzy_check_organization("SPD")
        assert any("Fuzzy organization check" in r.message for r in caplog.records)

    # --- fuzzy_match_acronym ---------------------------------------------

    def test_fuzzy_match_acronym_exact(self, resolver: OrganizationResolver) -> None:
        assert resolver.fuzzy_match_acronym("SPD") == "SPD"

    def test_fuzzy_match_acronym_fuzzy(self, resolver: OrganizationResolver) -> None:
        assert resolver.fuzzy_match_acronym("Sozialdemokratische Partei") == "SPD"

    def test_fuzzy_match_acronym_unresolved_returns_query(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.fuzzy_match_acronym("Piratenpartei") == "Piratenpartei"

    def test_fuzzy_match_acronym_no_acronym_returns_query(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.fuzzy_match_acronym("Adidas AG") == "Adidas AG"

    def test_fuzzy_match_acronym_debug_log_matched(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.fuzzy_match_acronym("SPD")
        assert any("returning acronym" in r.message for r in caplog.records)

    def test_fuzzy_match_acronym_debug_log_unresolved(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.fuzzy_match_acronym("Piratenpartei")
        assert any("unresolved, returning query" in r.message for r in caplog.records)

    # --- canonicalize_organization ----------------------------------------

    def test_canonicalize_organization_resolved(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.canonicalize_organization("SPD") == "SPD"

    def test_canonicalize_organization_unresolved_non_strict(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.canonicalize_organization("Piratenpartei") == "Piratenpartei"

    def test_canonicalize_organization_unresolved_strict(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.canonicalize_organization("Piratenpartei", strict=True) is None

    def test_canonicalize_organization_debug_log_resolved(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.canonicalize_organization("SPD")
        assert any("Resolved organization" in r.message for r in caplog.records)

    def test_canonicalize_organization_debug_log_unresolved(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.organizations"
        ):
            resolver.canonicalize_organization("Piratenpartei")
        assert any("unresolved, keeping original" in r.message for r in caplog.records)

    # --- canonicalize_organizations --------------------------------------

    def test_canonicalize_organizations_basic(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.canonicalize_organizations(["SPD", "FDP"]) == ["SPD", "FDP"]

    def test_canonicalize_organizations_unmatched_kept(
        self, resolver: OrganizationResolver
    ) -> None:
        result = resolver.canonicalize_organizations(["SPD", "Piratenpartei"])
        assert result == ["SPD", "Piratenpartei"]

    def test_canonicalize_organizations_strict_drops_unmatched(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.canonicalize_organizations(
            ["SPD", "Piratenpartei"], strict=True
        ) == ["SPD"]

    # --- get_organization_by_id ------------------------------------------

    def test_get_organization_by_id_hit(self, resolver: OrganizationResolver) -> None:
        org = resolver.get_organization_by_id("spd")
        assert org is not None
        assert org.id == "spd"
        assert org.canonical_name == "SPD"

    def test_get_organization_by_id_miss(self, resolver: OrganizationResolver) -> None:
        assert resolver.get_organization_by_id("does-not-exist") is None

    # --- get_organizations_by_acronym ------------------------------------

    def test_get_organizations_by_acronym_known(
        self, resolver: OrganizationResolver
    ) -> None:
        orgs = resolver.get_organizations_by_acronym("SPD")
        assert len(orgs) == 1
        assert orgs[0].id == "spd"

    def test_get_organizations_by_acronym_unknown(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.get_organizations_by_acronym("XYZ") == []

    def test_get_organizations_by_acronym_case_sensitive(
        self, resolver: OrganizationResolver
    ) -> None:
        assert resolver.get_organizations_by_acronym("spd") == []

    # --- explain ---------------------------------------------------------

    def test_explain_exact_hit(self, resolver: OrganizationResolver) -> None:
        trace = resolver.explain("SPD")
        assert trace["query"] == "SPD"
        assert trace["exact_hit"] is True
        assert len(trace["top_k"]) == 1
        assert trace["top_k"][0]["id"] == "spd"
        assert trace["top_k"][0]["score"] == 100.0

    def test_explain_fuzzy_ranks_candidates(
        self, resolver: OrganizationResolver
    ) -> None:
        trace = resolver.explain("Sozialdemokratische Partei", k=3)
        assert trace["exact_hit"] is False
        assert len(trace["top_k"]) == 3
        assert trace["top_k"][0]["id"] == "spd"
        scores = [c["score"] for c in trace["top_k"]]
        assert scores == sorted(scores, reverse=True)

    def test_explain_empty_query(self, resolver: OrganizationResolver) -> None:
        trace = resolver.explain("")
        assert trace["normalized_key"] == ""
        assert trace["exact_hit"] is False
        assert trace["top_k"] == []

    def test_explain_thresholds_match_defaults(
        self, resolver: OrganizationResolver
    ) -> None:
        trace = resolver.explain("SPD")
        assert trace["threshold"] == 80.0
        assert trace["near_tie_epsilon"] == 2.0

    def test_explain_k_caps_results(self, resolver: OrganizationResolver) -> None:
        assert len(resolver.explain("Sozialdemokratische Partei", k=2)["top_k"]) == 2

    def test_explain_empty_resolver(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("names: []\n")
        trace = OrganizationResolver(files=[empty]).explain("SPD")
        assert trace["top_k"] == []
        assert trace["exact_hit"] is False


# ---------------------------------------------------------------------------
# Integration — cross-resolver key consistency and public API surface
# ---------------------------------------------------------------------------


class TestIntegration:
    """Verify shared normalisation pipeline and importable public API surface."""

    @pytest.fixture(scope="class")
    def authors(self) -> AuthorResolver:
        return AuthorResolver()

    @pytest.fixture(scope="class")
    def orgs(self) -> OrganizationResolver:
        return OrganizationResolver()

    # --- public API surface -----------------------------------------------

    def test_resolution_models_importable(self) -> None:
        assert AuthorIDResolution is not None
        assert OrganizationIDResolution is not None
        assert NameIDResolution is not None

    def test_normalize_name_key_importable(self) -> None:
        assert callable(normalize_name_key)

    def test_author_resolve_returns_author_id_resolution(
        self, authors: AuthorResolver
    ) -> None:
        r = authors.resolve("Angela Merkel")
        assert isinstance(r, AuthorIDResolution)
        assert isinstance(r, NameIDResolution)

    def test_org_resolve_returns_org_id_resolution(
        self, orgs: OrganizationResolver
    ) -> None:
        r = orgs.resolve("SPD")
        assert isinstance(r, OrganizationIDResolution)
        assert isinstance(r, NameIDResolution)

    # --- shared normalisation pipeline ------------------------------------

    def test_normalize_name_is_idempotent(self) -> None:
        for s in [
            "Dr. Angela Merkel MdB",
            "Scholz, Olaf",
            "CDU/CSU",
            "Bündnis 90/Die Grünen",
        ]:
            key = normalize_name(s)
            assert normalize_name(key) == key, f"Not idempotent for: {s!r}"

    def test_normalize_name_key_is_idempotent(self) -> None:
        for s in ["Müller, Maria", "CDU/CSU", "Bündnis 90/Die Grünen", "Dr. Schmidt"]:
            key = normalize_name_key(s)
            assert normalize_name_key(key) == key, f"Not idempotent for: {s!r}"

    def test_umlaut_folding_consistent(self) -> None:
        assert normalize_name("Müller") == normalize_name("Mueller")
        assert normalize_name("Grüne") == normalize_name("Gruene")
        assert normalize_name_key("Müller") == normalize_name_key("Mueller")

    # --- canonical-name round-trip ----------------------------------------

    def test_author_canonical_name_round_trips_to_registered_key(
        self, authors: AuthorResolver
    ) -> None:
        for name in ["Angela Merkel", "Olaf Scholz", "Helmut Schmidt"]:
            r = authors.resolve(name)
            assert r.matched
            assert normalize_name(r.canonical_name) in authors._key_to_author

    def test_org_canonical_name_round_trips_to_registered_key(
        self, orgs: OrganizationResolver
    ) -> None:
        for name in ["SPD", "CDU", "FDP"]:
            r = orgs.resolve(name)
            assert r.matched
            assert normalize_name(r.canonical_name) in orgs._key_to_org

    # --- batch vs single consistency -------------------------------------

    def test_canonicalize_authors_matches_individual_resolve(
        self, authors: AuthorResolver
    ) -> None:
        names = ["Angela Merkel", "Olaf Scholz", "Helmut Schmidt"]
        assert authors.canonicalize_authors(names) == [
            authors.resolve(n).canonical_name for n in names
        ]

    def test_resolve_batch_matches_individual_resolve(
        self, orgs: OrganizationResolver
    ) -> None:
        names = ["SPD", "FDP", "CDU", "Bündnis 90/Die Grünen"]
        batch = orgs.resolve_batch(names)
        singles = [orgs.resolve(n) for n in names]
        assert [r.resolved_id for r in batch] == [r.resolved_id for r in singles]
        assert [r.score for r in batch] == [r.score for r in singles]
        assert [r.acronym for r in batch] == [r.acronym for r in singles]

    # --- acronym propagation ---------------------------------------------

    def test_acronym_consistent_between_single_and_batch(
        self, orgs: OrganizationResolver
    ) -> None:
        names = ["Sozialdemokratische Partei Deutschlands", "FDP", "CDU"]
        singles = [orgs.resolve(n) for n in names]
        batch = orgs.resolve_batch(names)
        for single, batched in zip(singles, batch):
            assert single.matched
            assert single.acronym == batched.acronym

    # --- matched / changed semantics -------------------------------------

    def test_exact_canonical_form_not_changed(self, authors: AuthorResolver) -> None:
        r = authors.resolve("Olaf Scholz")
        assert r.matched and not r.changed

    def test_alias_form_is_changed(self, authors: AuthorResolver) -> None:
        r = authors.resolve("Scholz, Olaf")
        assert r.matched and r.changed

    def test_unresolved_author_not_changed(self, authors: AuthorResolver) -> None:
        r = authors.resolve("Max Mustermann")
        assert not r.matched and not r.changed

    def test_unresolved_org_not_changed(self, orgs: OrganizationResolver) -> None:
        r = orgs.resolve("Piratenpartei")
        assert not r.matched and not r.changed


# ---------------------------------------------------------------------------
# normalize_autor
# ---------------------------------------------------------------------------


class TestNormalizeAutor:
    @pytest.fixture(scope="class")
    def author_resolver(self) -> AuthorResolver:
        return AuthorResolver()

    @pytest.fixture(scope="class")
    def org_resolver(self) -> OrganizationResolver:
        return OrganizationResolver()

    def test_organisation_resolved_to_canonical(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="Sozialdemokraten")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.organisation == "SPD"

    def test_organisation_alias_resolved(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="Christdemokraten")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.organisation == "CDU"

    def test_unknown_organisation_unchanged(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="Piratenpartei")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.organisation == "Piratenpartei"

    def test_person_resolved_to_canonical(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="SPD", person="Scholz, Olaf")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.person == "Olaf Scholz"

    def test_person_with_honorific_resolved(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="CDU", person="Dr. Angela Merkel")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.person == "Angela Merkel"

    def test_unknown_person_unchanged(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="SPD", person="Max Mustermann")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.person == "Max Mustermann"

    def test_none_person_not_touched(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="SPD", person=None)
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.person is None

    def test_whitespace_only_person_normalized_to_none_by_model(self) -> None:
        """A blank ``person`` becomes ``None`` while the Autor is being built.

        ``_blank_to_none`` on ``PaZuFaBaseModel`` maps blank strings on optional
        fields to ``None``, so the normaliser no longer sees the value. Asserting
        it here keeps the guarantee under test at the level where it now lives.
        """
        assert Autor(organisation="SPD", person="   ").person is None

    def test_whitespace_only_person_after_assignment_normalized_to_none(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="SPD", person="Erika Mustermann")
        item.person = "   "
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.person is None

    def test_empty_organisation_rejected_by_model(self) -> None:
        """A blank organisation is rejected while the Autor is being built.

        ``str_min_length`` on ``PaZuFaBaseModel`` catches this before
        ``normalize_autor`` ever sees the value, so the check has moved from the
        normaliser to the model. The normaliser keeps its own guard because
        ``validate_assignment`` is off: assigning a blank string after
        construction still slips past the model.
        """
        with pytest.raises(ValidationError):
            Autor(organisation="   ")

    def test_empty_organisation_after_assignment_raises(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="SPD")
        item.organisation = "   "
        with pytest.warns(DeprecationWarning), pytest.raises(ValueError):
            normalize_autor(item, author_resolver, org_resolver)

    def test_unresolved_organisation_debug_log(
        self,
        author_resolver: AuthorResolver,
        org_resolver: OrganizationResolver,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        item = Autor(organisation="Piratenpartei")
        with (
            pytest.warns(DeprecationWarning),
            caplog.at_level(
                logging.DEBUG, logger="pazufa_corelib.normalization.experimental"
            ),
        ):
            normalize_autor(item, author_resolver, org_resolver)
        assert any("organization not resolvable" in r.message for r in caplog.records)

    def test_none_person_debug_log(
        self,
        author_resolver: AuthorResolver,
        org_resolver: OrganizationResolver,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        item = Autor(organisation="SPD", person=None)
        with (
            pytest.warns(DeprecationWarning),
            caplog.at_level(
                logging.DEBUG, logger="pazufa_corelib.normalization.experimental"
            ),
        ):
            normalize_autor(item, author_resolver, org_resolver)
        assert any("author person empty" in r.message for r in caplog.records)

    def test_unresolved_person_debug_log(
        self,
        author_resolver: AuthorResolver,
        org_resolver: OrganizationResolver,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        item = Autor(organisation="SPD", person="Max Mustermann")
        with (
            pytest.warns(DeprecationWarning),
            caplog.at_level(
                logging.DEBUG, logger="pazufa_corelib.normalization.experimental"
            ),
        ):
            normalize_autor(item, author_resolver, org_resolver)
        assert any("author not resolvable" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# SchlagwortResolver
# ---------------------------------------------------------------------------


class TestSchlagwortResolver:
    @pytest.fixture(scope="class")
    def resolver(self) -> SchlagwortResolver:
        return SchlagwortResolver()

    # explain ---------------------------------------------------------------
    def test_explain_exact_hit_returns_single_top_match(
        self, resolver: SchlagwortResolver
    ) -> None:
        trace = resolver.explain("Digitalisierung")
        assert trace["query"] == "Digitalisierung"
        assert trace["exact_hit"] is True
        assert len(trace["top_k"]) == 1
        assert trace["top_k"][0]["id"] == "Digitalisierung"
        assert trace["top_k"][0]["score"] == 100.0

    def test_explain_fuzzy_hit_ranks_candidates(
        self, resolver: SchlagwortResolver
    ) -> None:
        trace = resolver.explain("Digitalisierumg", k=3)
        assert trace["exact_hit"] is False
        assert len(trace["top_k"]) == 3
        assert trace["top_k"][0]["id"] == "Digitalisierung"
        scores = [c["score"] for c in trace["top_k"]]
        assert scores == sorted(scores, reverse=True)

    def test_explain_empty_query_returns_empty_top_k(
        self, resolver: SchlagwortResolver
    ) -> None:
        trace = resolver.explain("")
        assert trace["processed_query"] == ""
        assert trace["exact_hit"] is False
        assert trace["top_k"] == []

    def test_explain_includes_thresholds(self, resolver: SchlagwortResolver) -> None:
        trace = resolver.explain("Digitalisierung")
        assert trace["threshold"] == 90.0
        assert trace["near_tie_epsilon"] == 1.0

    def test_explain_k_caps_top_k_length(self, resolver: SchlagwortResolver) -> None:
        trace = resolver.explain("Digitalisierumg", k=2)
        assert len(trace["top_k"]) == 2

    def test_explain_empty_resolver_returns_empty_top_k(self, tmp_path: Path) -> None:
        empty_tags = tmp_path / "empty_tags.yaml"
        empty_sachgebiete = tmp_path / "empty_sachgebiete.yaml"
        empty_tags.write_text("tags: []\n")
        empty_sachgebiete.write_text("tags: []\n")
        with (
            patch(
                "pazufa_corelib.normalization.schlagworte._GLOBAL_TAGS_FILES",
                (empty_tags,),
            ),
            patch(
                "pazufa_corelib.normalization.schlagworte._SACHGEBIETE_FILES",
                (empty_sachgebiete,),
            ),
        ):
            resolver = SchlagwortResolver()
        trace = resolver.explain("Digitalisierung")
        assert trace["top_k"] == []
        assert trace["exact_hit"] is False
