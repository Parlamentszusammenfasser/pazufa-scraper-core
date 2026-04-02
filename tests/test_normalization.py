"""Tests for normalization utilities."""

import pytest

from collector_core.normalization import normalise_datum, normalise_volltext
from collector_core.normalization.text import _is_garbled, _paragraph_quality_score


class TestNormaliseVolltext:
    def test_nfkc_normalization(self) -> None:
        # fi ligature (U+FB01) decomposes to "fi"
        assert "fi" in normalise_volltext("\ufb01nden")

    def test_c1_controls_stripped(self) -> None:
        result = normalise_volltext("Hallo\x85Welt\x96hier")
        assert "\x85" not in result
        assert "\x96" not in result
        assert "HalloWelthier" == result

    def test_crlf_normalized(self) -> None:
        result = normalise_volltext("Zeile eins\r\nZeile zwei\rZeile drei")
        assert "\r" not in result
        assert "Zeile eins\nZeile zwei\nZeile drei" == result

    def test_angle_brackets_replaced(self) -> None:
        result = normalise_volltext("<poststelle@lfdi.bwl.de>")
        assert "<" not in result
        assert ">" not in result
        assert "\u2039poststelle@lfdi.bwl.de\u203a" == result

    def test_garbled_paragraph_removed(self) -> None:
        clean = "Dies ist ein normaler deutscher Absatz mit korrektem Text."
        garbled = "\u0180\u0181\u0182\u0183\u0184\u0185\u0186\u0187\u0188\u0189"
        text = f"{clean}\n\n{garbled}"
        result = normalise_volltext(text)
        assert clean in result
        assert garbled not in result

    def test_clean_text_unchanged(self) -> None:
        text = "Der Landtag von Baden-Württemberg hat beschlossen."
        result = normalise_volltext(text)
        assert result == text

    def test_empty_string(self) -> None:
        assert normalise_volltext("") == ""

    def test_mixed_quality_paragraphs(self) -> None:
        clean = "Die Landesregierung wird aufgefordert zu berichten."
        garbled = "ĚĞƌ&ƌĂŬƚŝŽŶ ǁćŚƌůĞŝƐƚƵŶŐ ŝƚĞůůƚ"
        text = f"{clean}\n\n{garbled}"
        result = normalise_volltext(text)
        assert clean in result
        assert "ĚĞƌ" not in result


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


class TestIsGarbled:
    def test_clean_text(self) -> None:
        assert _is_garbled("Dies ist normaler deutscher Text.") is False

    def test_garbled_text(self) -> None:
        assert _is_garbled("ĚĞƌ&ƌĂŬƚŝŽŶ ǁćŚƌůĞŝƐƚƵŶŐ") is True

    def test_empty_string(self) -> None:
        assert _is_garbled("") is False

    def test_borderline_below_threshold(self) -> None:
        # 1 extended char among 20+ alpha chars → <5%
        text = "abcdefghijklmnopqrstŭ"
        assert _is_garbled(text) is False


class TestNormaliseDatum:
    @pytest.mark.parametrize(
        ("input_date", "expected"),
        [
            ("02.04.2026", "2026-04-02"),
            ("2.4.2026", "2026-04-02"),
            ("2. April 2026", "2026-04-02"),
            ("2026-04-02", "2026-04-02"),
            ("1.1.2025", "2025-01-01"),
            ("15. Dezember 2024", "2024-12-15"),
            ("3. März 2023", "2023-03-03"),
            ("15 Oktober 2025", "2025-10-15"),
            # Abbreviated month names
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
            "29.02.2025",  # 2025 is not a leap year
        ],
    )
    def test_invalid_dates(self, input_date: str) -> None:
        with pytest.raises(ValueError):
            normalise_datum(input_date)

    def test_whitespace_stripped(self) -> None:
        assert normalise_datum("  02.04.2026  ") == "2026-04-02"
