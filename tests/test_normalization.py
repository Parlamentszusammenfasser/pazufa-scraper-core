"""Tests for normalization utilities."""

import pytest

from collector_core.normalization import normalise_datum, normalise_volltext
from collector_core.normalization.text import _paragraph_quality_score


# ---------------------------------------------------------------------------
# normalise_volltext
# ---------------------------------------------------------------------------


class TestNormaliseVolltextNfkc:
    def test_fi_ligature_decomposed(self) -> None:
        assert "fi" in normalise_volltext("\ufb01nden")

    def test_ff_ligature_decomposed(self) -> None:
        assert "ff" in normalise_volltext("\ufb00nen")

    def test_superscript_digits(self) -> None:
        # NFKC maps ² → 2
        assert "m2" in normalise_volltext("m\u00b2")

    def test_fullwidth_latin(self) -> None:
        # Ａ (U+FF21) → A
        assert normalise_volltext("\uff21ntrag") == "Antrag"


class TestNormaliseVolltextInvisibleChars:
    def test_soft_hyphen_stripped(self) -> None:
        result = normalise_volltext("Bundes\u00adtag")
        assert "\u00ad" not in result
        assert "Bundestag" in result

    def test_bom_stripped(self) -> None:
        result = normalise_volltext("\ufeffHallo Welt")
        assert "\ufeff" not in result
        assert result == "Hallo Welt"

    def test_zero_width_space_stripped(self) -> None:
        result = normalise_volltext("Hallo\u200bWelt")
        assert "\u200b" not in result
        assert "HalloWelt" in result

    def test_zwj_stripped(self) -> None:
        result = normalise_volltext("Hallo\u200dWelt")
        assert "\u200d" not in result

    def test_zwnj_stripped(self) -> None:
        result = normalise_volltext("Hallo\u200cWelt")
        assert "\u200c" not in result

    def test_multiple_invisible_chars_at_once(self) -> None:
        result = normalise_volltext("\ufeffBundes\u00adtag\u200b Berlin\u200c")
        assert result == "Bundestag Berlin"


class TestNormaliseVolltextC1Controls:
    def test_c1_controls_stripped(self) -> None:
        result = normalise_volltext("Hallo\x85Welt\x96hier")
        assert "\x85" not in result
        assert "\x96" not in result
        assert "HalloWelthier" == result

    def test_all_c1_range_stripped(self) -> None:
        # Every byte from 0x80 to 0x9F should be removed
        c1 = "".join(chr(c) for c in range(0x80, 0xA0))
        result = normalise_volltext(f"A{c1}B")
        assert result == "AB"

    def test_c1_only_string(self) -> None:
        c1_only = "".join(chr(c) for c in range(0x80, 0xA0))
        assert normalise_volltext(c1_only) == ""


class TestNormaliseVolltextLineEndings:
    def test_crlf_normalized(self) -> None:
        result = normalise_volltext("Zeile eins\r\nZeile zwei\rZeile drei")
        assert "\r" not in result
        assert "Zeile eins\nZeile zwei\nZeile drei" == result

    def test_bare_cr_normalized(self) -> None:
        result = normalise_volltext("Eins\rZwei\rDrei")
        assert "\r" not in result
        assert "Eins\nZwei\nDrei" == result

    def test_mixed_line_endings(self) -> None:
        result = normalise_volltext("Eins\r\nZwei\rDrei\nVier")
        assert result == "Eins\nZwei\nDrei\nVier"


class TestNormaliseVolltextHyphenBreak:
    def test_basic_rejoin(self) -> None:
        result = normalise_volltext("Landes-\nregierung beschlossen")
        assert "Landesregierung" in result

    def test_compound_word_rejoin(self) -> None:
        result = normalise_volltext("Gesetzentwurf zur Änderung des Bundes-\nnaturschutzgesetzes")
        assert "Bundesnaturschutzgesetzes" in result

    def test_hyphen_at_end_of_line_without_continuation(self) -> None:
        # Hyphen followed by blank line (paragraph break) should NOT rejoin
        result = normalise_volltext("Absatz eins-\n\nAbsatz zwei")
        assert "Absatz eins-" in result or "Absatz eins" in result
        assert "Absatz zwei" in result

    def test_hyphen_not_between_word_chars_untouched(self) -> None:
        # Hyphen followed by newline then space should not rejoin
        result = normalise_volltext("Ergebnis: 5-\n 3 Stimmen")
        assert "53" not in result

    def test_hyphen_with_crlf_rejoined(self) -> None:
        # CRLF is normalised to LF first, so the hyphen-break still fires
        result = normalise_volltext("Landes-\r\nregierung")
        assert "Landesregierung" in result

    def test_multiple_hyphen_breaks(self) -> None:
        text = "Bundes-\nregierung und Landes-\nparlament"
        result = normalise_volltext(text)
        assert "Bundesregierung" in result
        assert "Landesparlament" in result


class TestNormaliseVolltextMultiSpace:
    def test_double_spaces_collapsed(self) -> None:
        result = normalise_volltext("Der  Landtag   von   Baden-Württemberg")
        assert "  " not in result
        assert "Der Landtag von Baden-Württemberg" in result

    def test_tabs_collapsed(self) -> None:
        result = normalise_volltext("Spalte\t\tZwei")
        assert "\t" not in result
        assert "Spalte Zwei" in result

    def test_mixed_spaces_and_tabs(self) -> None:
        result = normalise_volltext("A \t B")
        assert result == "A B"

    def test_single_space_preserved(self) -> None:
        result = normalise_volltext("Hallo Welt")
        assert result == "Hallo Welt"

    def test_newlines_not_collapsed(self) -> None:
        # Paragraph-separating blank lines must survive
        text = "Absatz eins.\n\nAbsatz zwei."
        result = normalise_volltext(text)
        assert "\n\n" in result


class TestNormaliseVolltextParagraphQuality:
    def test_garbled_paragraph_removed(self) -> None:
        clean = "Dies ist ein normaler deutscher Absatz mit korrektem Text."
        garbled = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        text = f"{clean}\n\n{garbled}"
        result = normalise_volltext(text)
        assert clean in result
        assert garbled not in result

    def test_mixed_quality_paragraphs(self) -> None:
        clean = "Die Landesregierung wird aufgefordert zu berichten."
        garbled = "ĚĞƌ&ƌĂŬƚŝŽŶ ǁćŚƌůĞŝƐƚƵŶŐ ŝƚĞůůƚ"
        text = f"{clean}\n\n{garbled}"
        result = normalise_volltext(text)
        assert clean in result
        assert "ĚĞƌ" not in result

    def test_multiple_clean_paragraphs_preserved(self) -> None:
        p1 = "Der Landtag hat in seiner heutigen Sitzung beschlossen."
        p2 = "Die Landesregierung wird aufgefordert zu berichten."
        result = normalise_volltext(f"{p1}\n\n{p2}")
        assert p1 in result
        assert p2 in result
        assert "\n\n" in result

    def test_all_garbled_paragraphs_removed(self) -> None:
        g1 = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        g2 = "\u018a\u018b\u018c\u018d\u018e\u018f\u0190\u0191\u0192\u0193"
        result = normalise_volltext(f"{g1}\n\n{g2}")
        assert result == ""

    def test_short_paragraph_all_caps_kept(self) -> None:
        text = "EINLEITUNG\n\nDie Landesregierung wird aufgefordert zu berichten."
        result = normalise_volltext(text)
        assert "EINLEITUNG" in result


class TestNormaliseVolltextAngleBrackets:
    def test_angle_brackets_replaced(self) -> None:
        result = normalise_volltext("<poststelle@lfdi.bwl.de>")
        assert "<" not in result
        assert ">" not in result
        assert "\u2039poststelle@lfdi.bwl.de\u203a" == result

    def test_nested_angle_brackets(self) -> None:
        result = normalise_volltext("a < b > c")
        assert "<" not in result
        assert ">" not in result
        assert "\u2039" in result
        assert "\u203a" in result

    def test_no_angle_brackets_unchanged(self) -> None:
        text = "Normaler Text ohne Klammern"
        assert normalise_volltext(text) == text


class TestNormaliseVolltextEdgeCases:
    def test_empty_string(self) -> None:
        assert normalise_volltext("") == ""

    def test_whitespace_only(self) -> None:
        assert normalise_volltext("   \n\n   ") == ""

    def test_clean_text_unchanged(self) -> None:
        text = "Der Landtag von Baden-Württemberg hat beschlossen."
        assert normalise_volltext(text) == text

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert normalise_volltext("  Hallo Welt  ") == "Hallo Welt"

    def test_idempotent(self) -> None:
        # Applying normalisation twice should give the same result
        text = "Landes-\nregierung  hat\x85 beschlossen\r\n"
        once = normalise_volltext(text)
        twice = normalise_volltext(once)
        assert once == twice

    def test_full_pipeline_combined(self) -> None:
        # Exercises all steps at once: NFKC + invisible + C1 + CRLF +
        # hyphen-break + multi-space + garbled removal + angle brackets
        garbled = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        text = (
            "\ufeffDer  Landtag\x85 hat die Landes-\r\nregierung <aufgefordert>"
            f"\n\n{garbled}"
        )
        result = normalise_volltext(text)
        assert "\ufeff" not in result
        assert "\x85" not in result
        assert "\r" not in result
        assert "  " not in result
        assert "Landesregierung" in result
        assert "\u2039aufgefordert\u203a" in result
        assert garbled not in result

    def test_unicode_letters_in_hyphen_break(self) -> None:
        # German umlauts should be treated as word characters by \w
        result = normalise_volltext("Über-\ngangsregelung")
        assert "Übergangsregelung" in result


# ---------------------------------------------------------------------------
# normalise_volltext — characterisation tests for HTML input
#
# normalise_volltext expects plain text. These tests document its actual
# behaviour when HTML is passed in accidentally, so that regressions are
# visible and the limitations are explicit.
# ---------------------------------------------------------------------------


class TestNormaliseVolltextOnHtmlInput:
    """Characterise normalise_volltext behaviour on HTML input.

    normalise_volltext is NOT an HTML processor. These tests pin the current
    behaviour so that any unintentional change is caught, and so that the
    limitations are clearly documented for callers.
    """

    def test_plain_text_unaffected_by_unescape(self) -> None:
        # html.unescape() is a no-op on text with no entity sequences.
        text = "Der Landtag von Baden-Württemberg hat beschlossen."
        assert normalise_volltext(text) == text

    def test_html_tags_become_guillemets(self) -> None:
        # Tags are NOT stripped — angle brackets are replaced by ‹ ›.
        result = normalise_volltext("<p>Absatz</p>")
        assert "<" not in result
        assert ">" not in result
        assert "\u2039p\u203a" in result
        assert "Absatz" in result

    def test_html_named_entities_decoded(self) -> None:
        # html.unescape() runs first, so &amp; → & and &uuml; → ü.
        result = normalise_volltext("Titel &amp; Inhalt &uuml;ber alles")
        assert "&amp;" not in result
        assert "&uuml;" not in result
        assert "Titel & Inhalt über alles" == result

    def test_nbsp_entity_decoded_to_space(self) -> None:
        # &nbsp; → U+00A0, then NFKC collapses it to a regular space.
        result = normalise_volltext("Wort&nbsp;Wort")
        assert "&nbsp;" not in result
        assert "Wort Wort" == result

    def test_inline_tags_mangle_surrounding_text(self) -> None:
        # <b>…</b> becomes ‹b›…‹/b›, cluttering the output text.
        result = normalise_volltext("Ein <b>wichtiger</b> Antrag")
        assert "\u2039b\u203a" in result
        assert "\u2039/b\u203a" in result

    def test_paragraph_tag_not_a_line_break(self) -> None:
        # <p> does NOT create a paragraph break — it becomes a guillemet.
        # Text before and after stays on the same logical line.
        result = normalise_volltext("<p>Absatz eins</p><p>Absatz zwei</p>")
        assert "\n\n" not in result

    def test_br_tag_not_a_line_break(self) -> None:
        # <br> does NOT insert a newline — it becomes ‹br›.
        result = normalise_volltext("Zeile eins<br>Zeile zwei")
        assert "Zeile eins\nZeile zwei" not in result
        assert "\u2039br\u203a" in result

    def test_numeric_html_entity_decoded(self) -> None:
        # &#160; → U+00A0, then NFKC collapses it to a regular space.
        result = normalise_volltext("Wort&#160;Wort")
        assert "&#160;" not in result
        assert "Wort Wort" == result

    def test_html_heavy_paragraph_survives_quality_filter(self) -> None:
        # Tag names (div, span, href, …) contain vowels, so the vowelless
        # penalty stays low and the paragraph is NOT filtered out.
        html = '<div class="content"><span>Text</span></div>'
        result = normalise_volltext(html)
        assert result != ""

    def test_script_tag_content_survives(self) -> None:
        # <script> content is not executed or stripped — it passes through
        # with angle brackets replaced.
        result = normalise_volltext("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "alert(1)" in result


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
# normalise_datum
# ---------------------------------------------------------------------------


class TestNormaliseDatum:
    @pytest.mark.parametrize(
        ("input_date", "expected"),
        [
            # German dot notation
            ("02.04.2026", "2026-04-02"),
            ("2.4.2026", "2026-04-02"),
            ("1.1.2025", "2025-01-01"),
            ("31.12.2024", "2024-12-31"),
            # ISO 8601
            ("2026-04-02", "2026-04-02"),
            ("2024-01-01", "2024-01-01"),
            ("2024-12-31", "2024-12-31"),
            # German long format — full month names
            ("2. April 2026", "2026-04-02"),
            ("15. Dezember 2024", "2024-12-15"),
            ("3. März 2023", "2023-03-03"),
            ("15 Oktober 2025", "2025-10-15"),
            ("1 Mai 2024", "2024-05-01"),
            # German long format — abbreviated month names
            ("2. Jan. 2026", "2026-01-02"),
            ("2. Jan 2026", "2026-01-02"),
            ("15. Feb. 2024", "2024-02-15"),
            ("1. Mär. 2025", "2025-03-01"),
            ("1. Mrz. 2025", "2025-03-01"),
            ("5. Apr. 2023", "2023-04-05"),
            ("10. Jun. 2022", "2022-06-10"),
            ("7. Jul. 2021", "2021-07-07"),
            ("3. Aug. 2020", "2020-08-03"),
            ("9. Sep. 2026", "2026-09-09"),
            ("9. Sept. 2026", "2026-09-09"),
            ("4. Okt. 2025", "2025-10-04"),
            ("11. Nov. 2024", "2024-11-11"),
            ("24. Dez. 2023", "2023-12-24"),
            # Leap year
            ("29.02.2024", "2024-02-29"),
        ],
    )
    def test_valid_dates(self, input_date: str, expected: str) -> None:
        assert normalise_datum(input_date) == expected

    @pytest.mark.parametrize(
        "input_date",
        [
            "not a date",
            "",
            "32.13.2025",
            "29.02.2025",       # 2025 is not a leap year
            "00.01.2025",       # day 0 is invalid
            "01.00.2025",       # month 0 is invalid
            "01.13.2025",       # month 13 is invalid
            "2025-13-01",       # month 13 in ISO
            "2025-01-32",       # day 32 in ISO
            "5. Foobar 2025",   # unknown month name
            "abc-de-fg",        # letters in ISO format
        ],
    )
    def test_invalid_dates(self, input_date: str) -> None:
        with pytest.raises(ValueError):
            normalise_datum(input_date)

    def test_whitespace_stripped(self) -> None:
        assert normalise_datum("  02.04.2026  ") == "2026-04-02"

    def test_nbsp_in_long_format(self) -> None:
        assert normalise_datum("2.\u00a0April\u00a02026") == "2026-04-02"

    def test_narrow_no_break_space(self) -> None:
        # U+202F narrow no-break space — collapsed by NFKC
        assert normalise_datum("2.\u202fApril\u202f2026") == "2026-04-02"

    def test_month_name_case_insensitive(self) -> None:
        # The regex captures [A-Za-z…] and lowercases for lookup
        assert normalise_datum("2. april 2026") == "2026-04-02"
        assert normalise_datum("2. APRIL 2026") == "2026-04-02"

    def test_iso_passthrough_unchanged(self) -> None:
        # ISO dates should round-trip exactly
        assert normalise_datum("2026-04-02") == "2026-04-02"

    def test_boundary_dates(self) -> None:
        # Year regex requires exactly 4 digits
        assert normalise_datum("1.1.0001") == "0001-01-01"
        assert normalise_datum("31.12.9999") == "9999-12-31"
