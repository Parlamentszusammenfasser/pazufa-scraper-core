"""Helpers for working with the generated OpenAPI client.

The generated client takes header timestamps such as ``If-Modified-Since`` as
plain strings. To keep collectors from each rolling their own format, this
module exposes a small helper that produces the exact string the API expects
(matching the format documented in ``openapi.yaml``).

It also hosts upload-time checks: rules the backend enforces on ``PUT`` that
must not apply when the same models are used to read data back.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pazufa_corelib.api_model import Station, Vorgang

LOGGER = logging.getLogger(__name__)


class UploadValidationError(ValueError):
    """A model is valid on its own but would be rejected by the backend on upload."""


class PastStationError(UploadValidationError):
    """One or more Stationen start before now (backend No-Past-Stations-Rule).

    Attributes:
        stationen: The offending Stationen, in their order within the Vorgang,
            so callers can drop them instead of failing the whole upload.
        now: The reference time the Stationen were compared against.
    """

    def __init__(self, stationen: list[Station], now: datetime) -> None:
        self.stationen = stationen
        self.now = now
        starts = ", ".join(s.zp_start.isoformat() for s in stationen)
        super().__init__(
            f"{len(stationen)} Station(en) start before {now.isoformat()} "
            f"(No-Past-Stations-Rule): zp_start {starts}"
        )


def format_if_modified_since(value: datetime) -> str:
    """Format a datetime for use as an ``If-Modified-Since`` header value.

    The OpenAPI spec documents the format as ISO 8601 with an explicit
    timezone offset and whole-second precision (e.g.
    ``2024-01-01T00:00:00+00:00``). Microseconds are dropped before
    formatting so the output always matches that shape, regardless of how
    the input was constructed.

    Args:
        value: A timezone-aware datetime.

    Returns:
        The ISO 8601 representation, truncated to whole seconds, including
        the timezone offset.

    Raises:
        ValueError: If ``value`` is naive (has no timezone information).
    """
    if not _is_aware(value):
        raise ValueError("If-Modified-Since requires a timezone-aware datetime")
    return value.replace(microsecond=0).isoformat()


def validate_for_upload(vorgang: Vorgang, *, now: datetime | None = None) -> None:
    """Check upload-only backend rules on a `Vorgang` right before sending it.

    These rules are deliberately not model validators: a Station that was
    valid when uploaded becomes "past" later, and downloads must still parse.
    Call this as late as possible, since the result depends on the clock.

    Currently enforced:

    * **No-Past-Stations-Rule** — no Station may have a ``zp_start`` before
      now. A ``zp_start`` exactly equal to ``now`` is accepted.

    Args:
        vorgang: The Vorgang about to be uploaded.
        now: Reference time; defaults to the current UTC time. Pass a fixed
            value in tests or to check a batch against one consistent instant.

    Raises:
        ValueError: If ``now`` is naive (has no timezone information).
        PastStationError: If one or more Stationen start before ``now``. The
            exception carries the offending Stationen in ``stationen``.
    """
    if now is None:
        now = datetime.now(UTC)
    elif not _is_aware(now):
        raise ValueError("validate_for_upload requires a timezone-aware 'now'")

    past = [station for station in vorgang.stationen if station.zp_start < now]
    if past:
        LOGGER.warning(
            "Vorgang %s violates the No-Past-Stations-Rule: %d of %d Stationen "
            "start before %s",
            vorgang.api_id,
            len(past),
            len(vorgang.stationen),
            now.isoformat(),
        )
        raise PastStationError(past, now)


def _is_aware(value: datetime) -> bool:
    """Return whether ``value`` carries a usable timezone offset."""
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None
