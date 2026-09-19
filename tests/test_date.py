"""Tests for date normalization."""

import pytest

from pazufa_corelib.normalization.date import normalize_datum

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
