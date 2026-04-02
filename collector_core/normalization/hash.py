"""Hashing utilities for parliamentary documents."""

import hashlib

from .text import normalise_volltext

HASH_VARIANT_BYTES = "sha256+rawbytes"
HASH_VARIANT_TEXT = "sha256+text"


def hash_bytes(data: bytes) -> tuple[str, str]:
    """SHA-256 hash of raw bytes (used for PDFs).

    Hash is computed directly from the raw bytes without any normalisation.

    Returns a tuple of ``(hash, variant)`` where variant is ``"sha256+rawbytes"``.

    Raises :class:`TypeError` if *data* is not :class:`bytes`.
    """
    if not isinstance(data, bytes):
        raise TypeError(f"hash_bytes expects bytes, got {type(data).__name__}")
    return hashlib.sha256(data).hexdigest(), HASH_VARIANT_BYTES


def hash_text(text: str) -> tuple[str, str]:
    """SHA-256 hash of normalised text (used for HTML and pre-populated volltext).

    Hashes over the output of :func:`normalise_volltext` so that minor
    formatting differences do not produce different hashes for semantically
    identical documents.

    Returns a tuple of ``(hash, variant)`` where variant is ``"sha256+text"``.

    Raises :class:`TypeError` if *text* is not :class:`str`.
    """
    if not isinstance(text, str):
        raise TypeError(f"hash_text expects str, got {type(text).__name__}")
    normalised = normalise_volltext(text).encode("utf-8")
    return hashlib.sha256(normalised).hexdigest(), HASH_VARIANT_TEXT
