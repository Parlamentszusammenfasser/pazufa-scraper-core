"""Helpers for working with the generated OpenAPI client.

The generated client takes header timestamps such as ``If-Modified-Since`` as
plain strings. To keep collectors from each rolling their own format, this
module exposes a small helper that produces the exact string the API expects
(matching the format documented in ``openapi.yaml``).
"""

from datetime import datetime


def format_if_modified_since(value: datetime) -> str:
    """Format a datetime for use as an ``If-Modified-Since`` header value.

    The OpenAPI spec documents the format as ISO 8601 with an explicit
    timezone offset (e.g. ``2024-01-01T00:00:00+00:00``). ``datetime.isoformat``
    already produces that shape for timezone-aware values.

    Args:
        value: A timezone-aware datetime.

    Returns:
        The ISO 8601 representation including the timezone offset.

    Raises:
        ValueError: If ``value`` is naive (has no timezone information).
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("If-Modified-Since requires a timezone-aware datetime")
    return value.isoformat()
