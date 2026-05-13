"""Tests for normalization utilities."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from pazufa_corelib.api_model import Autor
from pazufa_corelib.normalization import (
    AuthorIDResolution,
    AuthorResolver,
    NameIDResolution,
    OrganizationIDResolution,
    OrganizationResolver,
    normalize_datum,
    normalize_name,
    normalize_name_key,
    normalize_volltext,
)
from pazufa_corelib.normalization.names import normalize_autor
from pazufa_corelib.normalization.schlagworte import SchlagwortResolver
from pazufa_corelib.normalization.text import _paragraph_quality_score

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
# normalize_volltext — HTML input characterisation
#
# Tags are NOT stripped — only entities are decoded. These tests document
# the predictable behaviour so callers know what to expect.
# ---------------------------------------------------------------------------


class TestnormalizeVolltextOnHtmlInput:
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

    def test_html_tags_become_guillemets(self) -> None:
        # Tags are NOT stripped — angle brackets are replaced by ‹ ›.
        result = normalize_volltext("<p>Absatz</p>")
        assert "<" not in result
        assert "\u2039p\u203a" in result
        assert "Absatz" in result

    def test_inline_tags_mangle_surrounding_text(self) -> None:
        result = normalize_volltext("Ein <b>wichtiger</b> Antrag")
        assert "\u2039b\u203a" in result
        assert "\u2039/b\u203a" in result

    def test_paragraph_tag_not_a_line_break(self) -> None:
        result = normalize_volltext("<p>Absatz eins</p><p>Absatz zwei</p>")
        assert "\n\n" not in result

    def test_br_tag_not_a_line_break(self) -> None:
        result = normalize_volltext("Zeile eins<br>Zeile zwei")
        assert "Zeile eins\nZeile zwei" not in result
        assert "\u2039br\u203a" in result

    def test_script_tag_content_survives(self) -> None:
        result = normalize_volltext("<script>alert(1)</script>")
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
# normalize_datum
# ---------------------------------------------------------------------------


class TestnormalizeDatum:
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
        assert normalize_datum(input_date) == expected

    @pytest.mark.parametrize(
        "input_date",
        [
            "not a date",
            "",
            "32.13.2025",
            "29.02.2025",  # 2025 is not a leap year
            "00.01.2025",  # day 0 is invalid
            "01.00.2025",  # month 0 is invalid
            "01.13.2025",  # month 13 is invalid
            "2025-13-01",  # month 13 in ISO
            "2025-01-32",  # day 32 in ISO
            "5. Foobar 2025",  # unknown month name
            "abc-de-fg",  # letters in ISO format
        ],
    )
    def test_invalid_dates(self, input_date: str) -> None:
        with pytest.raises(ValueError):
            normalize_datum(input_date)

    def test_whitespace_stripped(self) -> None:
        assert normalize_datum("  02.04.2026  ") == "2026-04-02"

    def test_nbsp_in_long_format(self) -> None:
        assert normalize_datum("2.\u00a0April\u00a02026") == "2026-04-02"

    def test_narrow_no_break_space(self) -> None:
        # U+202F narrow no-break space — collapsed by NFKC
        assert normalize_datum("2.\u202fApril\u202f2026") == "2026-04-02"

    def test_month_name_case_insensitive(self) -> None:
        # The regex captures [A-Za-z…] and lowercases for lookup
        assert normalize_datum("2. april 2026") == "2026-04-02"
        assert normalize_datum("2. APRIL 2026") == "2026-04-02"

    def test_iso_passthrough_unchanged(self) -> None:
        # ISO dates should round-trip exactly
        assert normalize_datum("2026-04-02") == "2026-04-02"

    def test_boundary_dates(self) -> None:
        # Year regex requires exactly 4 digits
        assert normalize_datum("1.1.0001") == "0001-01-01"
        assert normalize_datum("31.12.9999") == "9999-12-31"


# ---------------------------------------------------------------------------
# normalize_name_key
# ---------------------------------------------------------------------------


class TestNormalizeNameKey:
    def test_nfkc_ligature(self) -> None:
        assert normalize_name_key("ﬁscher") == "fischer"

    def test_umlaut_fold_u(self) -> None:
        assert normalize_name_key("Müller") == "mueller"

    def test_umlaut_fold_o(self) -> None:
        assert normalize_name_key("Möller") == "moeller"

    def test_umlaut_fold_a(self) -> None:
        assert normalize_name_key("Bäcker") == "baecker"

    def test_umlaut_fold_sz(self) -> None:
        assert normalize_name_key("Straße") == "strasse"

    def test_lowercase(self) -> None:
        assert normalize_name_key("MUELLER") == "mueller"

    def test_punctuation_stripped(self) -> None:
        assert normalize_name_key("Müller, Maria") == "mueller maria"

    def test_hyphen_stripped(self) -> None:
        assert normalize_name_key("Müller-Franken") == "muellerfranken"

    def test_whitespace_collapsed(self) -> None:
        assert normalize_name_key("  Maria   Müller  ") == "maria mueller"

    def test_invisible_chars_stripped(self) -> None:
        assert normalize_name_key("Mül​ler") == "mueller"

    def test_empty_string(self) -> None:
        assert normalize_name_key("") == ""

    def test_mueller_variants_equal(self) -> None:
        assert normalize_name_key("Müller") == normalize_name_key("Mueller")

    def test_idempotent(self) -> None:
        key = normalize_name_key("Dr. María Ångström")
        assert normalize_name_key(key) == key


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_token_sort_firstname_lastname(self) -> None:
        assert normalize_name("Maria Müller") == normalize_name("Müller Maria")

    def test_token_sort_comma_form(self) -> None:
        assert normalize_name("Müller, Maria") == normalize_name("Maria Müller")

    def test_honorific_dr_stripped(self) -> None:
        assert normalize_name("Dr. Maria Müller") == normalize_name("Maria Müller")

    def test_honorific_prof_stripped(self) -> None:
        assert normalize_name("Prof. Schmidt") == normalize_name("Schmidt")

    def test_honorific_prof_dr_stripped(self) -> None:
        assert normalize_name("Prof. Dr. Schmidt") == normalize_name("Schmidt")

    def test_honorific_mdb_stripped(self) -> None:
        assert normalize_name("Maria Müller MdB") == normalize_name("Maria Müller")

    def test_honorific_mdl_stripped(self) -> None:
        assert normalize_name("Hans Maier MdL") == normalize_name("Hans Maier")

    def test_honorific_dipl_stripped(self) -> None:
        assert normalize_name("Dipl.-Ing. Bernd Weber") == normalize_name("Bernd Weber")

    def test_umlaut_fold_applied(self) -> None:
        assert normalize_name("Müller") == normalize_name("Mueller")

    def test_combined_honorific_umlaut_sort(self) -> None:
        assert normalize_name("Dr. Maria Müller MdB") == normalize_name("mueller maria")

    def test_empty_string(self) -> None:
        assert normalize_name("") == ""

    def test_whitespace_only(self) -> None:
        assert normalize_name("   ") == ""

    def test_integration_same_key_from_different_forms(self) -> None:
        variants = [
            "Dr. Maria Müller",
            "Müller, Maria",
            "Mueller, Maria",
            "Maria Mueller",
            "Dr. Müller, Maria MdL",
        ]
        keys = [normalize_name(v) for v in variants]
        assert len(set(keys)) == 1, f"Expected one unique key, got: {set(keys)}"


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
            AuthorResolver(near_tie_epsilon=5.0).explain("Olaf Scholz")["near_tie_epsilon"]
            == 5.0
        )

    def test_init_emits_debug_log(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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
        assert not AuthorResolver(match_threshold=100.0).resolve("Helmut Schmitt").matched

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
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
        ):
            resolver.canonicalize_author("Olaf Scholz")
        assert any("Resolved author" in r.message for r in caplog.records)

    def test_canonicalize_author_debug_log_unresolved(
        self, resolver: AuthorResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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
            OrganizationResolver(near_tie_epsilon=10.0).explain("SPD")["near_tie_epsilon"]
            == 10.0
        )

    def test_init_emits_debug_log(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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

    def test_exact_via_slash_normalisation(self, resolver: OrganizationResolver) -> None:
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
        strict = OrganizationResolver(
            match_threshold=default.score + 1.0
        ).resolve("Sozialdemokratische Partei")
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
        assert resolver.resolve("Sozialdemokratische Partei Deutschlands").acronym == "SPD"

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
            logging.WARNING, logger="pazufa_corelib.normalization.names"
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
            logging.WARNING, logger="pazufa_corelib.normalization.names"
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
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
        ):
            resolver.fuzzy_match_acronym("SPD")
        assert any("returning acronym" in r.message for r in caplog.records)

    def test_fuzzy_match_acronym_debug_log_unresolved(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
        ):
            resolver.canonicalize_organization("SPD")
        assert any("Resolved organization" in r.message for r in caplog.records)

    def test_canonicalize_organization_debug_log_unresolved(
        self, resolver: OrganizationResolver, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(
            logging.DEBUG, logger="pazufa_corelib.normalization.names"
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

    def test_whitespace_only_person_normalized_to_none(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="SPD", person="   ")
        with pytest.warns(DeprecationWarning):
            normalize_autor(item, author_resolver, org_resolver)
        assert item.person is None

    def test_empty_organisation_raises(
        self, author_resolver: AuthorResolver, org_resolver: OrganizationResolver
    ) -> None:
        item = Autor(organisation="   ")
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
            caplog.at_level(logging.DEBUG, logger="pazufa_corelib.normalization.names"),
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
            caplog.at_level(logging.DEBUG, logger="pazufa_corelib.normalization.names"),
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
            caplog.at_level(logging.DEBUG, logger="pazufa_corelib.normalization.names"),
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
