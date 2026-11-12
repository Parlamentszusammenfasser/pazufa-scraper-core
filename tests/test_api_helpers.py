"""Tests for API client helpers."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from pazufa_corelib.api_helpers import (
    PastStationError,
    format_if_modified_since,
    validate_for_upload,
)
from pazufa_corelib.api_model import (
    Gremium,
    Parlament,
    Station,
    Stationstyp,
    Vorgang,
    Vorgangstyp,
)


def test_formats_utc_datetime_with_offset() -> None:
    value = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert format_if_modified_since(value) == "2024-01-01T00:00:00+00:00"


def test_formats_non_utc_offset() -> None:
    value = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone(timedelta(hours=2)))
    assert format_if_modified_since(value) == "2024-06-15T12:30:00+02:00"


def test_drops_microseconds() -> None:
    value = datetime(2024, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
    assert format_if_modified_since(value) == "2024-01-01T00:00:00+00:00"


def test_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        format_if_modified_since(datetime(2024, 1, 1, 0, 0, 0))  # noqa: DTZ001  # naive datetime is the rejection case under test


# ---------------------------------------------------------------------------
# validate_for_upload — No-Past-Stations-Rule
# ---------------------------------------------------------------------------

NOW = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
HELPERS_LOGGER = "pazufa_corelib.api_helpers"


def _station(zp_start: datetime | None) -> Station:
    return Station(
        typ=Stationstyp.preparl_formvs,
        dokumente=[],
        zp_start=zp_start,
        gremium=Gremium(name="Plenum", parlament=Parlament.BW, wahlperiode=17),
    )


def _vorgang(*starts: datetime | None) -> Vorgang:
    return Vorgang(
        api_id=uuid4(),
        initiatoren=[],
        stationen=[_station(s) for s in starts],
        titel="Gesetz zur Testung",
        typ=Vorgangstyp.bu_einspruch_inibreg,
        verfassungsaendernd=False,
        wahlperiode=17,
    )


def test_upload_accepts_future_stationen() -> None:
    validate_for_upload(_vorgang(NOW + timedelta(days=1)), now=NOW)


def test_upload_accepts_zp_start_equal_to_now() -> None:
    """The rule is "less than now", so the boundary itself is allowed."""
    validate_for_upload(_vorgang(NOW), now=NOW)


def test_upload_accepts_vorgang_without_stationen() -> None:
    validate_for_upload(_vorgang(), now=NOW)


def test_upload_rejects_past_station() -> None:
    with pytest.raises(PastStationError, match="No-Past-Stations-Rule"):
        validate_for_upload(_vorgang(NOW - timedelta(seconds=1)), now=NOW)


def test_upload_error_lists_only_the_past_stationen_in_order() -> None:
    old = NOW - timedelta(days=30)
    older = NOW - timedelta(days=60)
    vorgang = _vorgang(old, NOW + timedelta(days=1), older)

    with pytest.raises(PastStationError) as exc_info:
        validate_for_upload(vorgang, now=NOW)

    err = exc_info.value
    assert [s.zp_start for s in err.stationen] == [old, older]
    assert err.stationen[0] is vorgang.stationen[0]
    assert err.now == NOW
    assert "2 Station(en)" in str(err)


def test_upload_error_is_a_value_error() -> None:
    """Callers catching ValueError (as for pydantic rules) still catch it."""
    with pytest.raises(ValueError):
        validate_for_upload(_vorgang(NOW - timedelta(days=1)), now=NOW)


def test_upload_compares_across_timezones() -> None:
    """12:30+02:00 is 10:30 UTC, i.e. before NOW (12:00 UTC)."""
    cest = timezone(timedelta(hours=2))
    with pytest.raises(PastStationError):
        validate_for_upload(
            _vorgang(datetime(2026, 11, 12, 12, 30, tzinfo=cest)), now=NOW
        )


def test_upload_rejects_naive_now() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_for_upload(_vorgang(), now=datetime(2026, 1, 1))  # noqa: DTZ001  # naive datetime is the rejection case under test


def test_upload_defaults_now_to_current_time() -> None:
    validate_for_upload(_vorgang(datetime.now(timezone.utc) + timedelta(days=1)))
    with pytest.raises(PastStationError):
        validate_for_upload(_vorgang(datetime.now(timezone.utc) - timedelta(days=1)))


def test_upload_logs_violation(caplog: pytest.LogCaptureFixture) -> None:
    vorgang = _vorgang(NOW - timedelta(days=1), NOW + timedelta(days=1))
    with caplog.at_level(logging.WARNING, logger=HELPERS_LOGGER):
        with pytest.raises(PastStationError):
            validate_for_upload(vorgang, now=NOW)
    assert str(vorgang.api_id) in caplog.text
    assert "1 of 2 Stationen" in caplog.text


def test_downloaded_past_station_still_parses() -> None:
    """The rule must not leak into the model: reading old data has to work."""
    station = Station.model_validate(
        {
            "typ": "preparl-formvs",
            "dokumente": [],
            "zp_start": "2020-01-01T00:00:00+00:00",
            "gremium": {"name": "Plenum", "parlament": "BW", "wahlperiode": 17},
        }
    )
    assert station.zp_start is not None
    assert station.zp_start.year == 2020


def test_upload_ignores_station_without_zp_start() -> None:
    """``zp_start`` is optional since spec 0.2.9; no start cannot be in the past."""
    validate_for_upload(_vorgang(None, NOW + timedelta(days=1)), now=NOW)


def test_upload_reports_past_station_next_to_one_without_zp_start() -> None:
    past = NOW - timedelta(days=1)
    with pytest.raises(PastStationError) as exc_info:
        validate_for_upload(_vorgang(None, past), now=NOW)
    assert [s.zp_start for s in exc_info.value.stationen] == [past]
