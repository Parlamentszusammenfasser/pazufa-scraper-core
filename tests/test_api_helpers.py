"""Tests for API client helpers."""

from datetime import datetime, timedelta, timezone

import pytest

from corelib.api_helpers import format_if_modified_since


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
        format_if_modified_since(datetime(2024, 1, 1, 0, 0, 0))
