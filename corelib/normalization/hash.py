"""Hashing utilities for parliamentary documents."""

import hashlib
import logging
from inspect import stack
from typing import Any

from .text import normalize_volltext

# =====================================================================
# Constants
# =====================================================================
LOGGER = logging.getLogger(__name__)

HASH_ALGORITHM_SHA_256 = "sha256"
HASH_ALGORITHM_SHA_1 = "sha1"

HASH_CONNECTOR = "+"

HASH_VARIANT_BYTES = "bytes"
HASH_VARIANT_TEXT = "text"


# =====================================================================
# Private Helper Functions
# =====================================================================


def _check_type(data: Any, expected_type: type) -> None:
    if not isinstance(data, expected_type):
        # information for error message
        caller_name = stack()[1].function
        actual_type_name = type(data).__name__
        expected_type_name = expected_type.__name__

        LOGGER.error(
            f"Type check failed in '{caller_name}': "
            f"expected {expected_type_name}, got {actual_type_name}"
        )

        raise TypeError(
            f"The function: {caller_name} expects "
            f"{expected_type_name}, got {actual_type_name}"
        )


# =====================================================================
# public singular hash functions
# =====================================================================


def hash_bytes_sha_1(data: bytes) -> tuple[str, str]:
    """SHA-1 hash of raw bytes (not implemented in Backend yet).

    Hash is computed directly from the raw bytes without any normalization.

    Returns a tuple of ``(hash, variant)`` where variant is ``"sha1+rawbytes"``.

    Raises :class:`TypeError` if *data* is not :class:`bytes`.
    """
    _check_type(data, bytes)

    hash_content = hashlib.sha1(data).hexdigest()
    hash_type = HASH_ALGORITHM_SHA_1 + HASH_CONNECTOR + HASH_VARIANT_BYTES

    return hash_content, hash_type


def hash_bytes_sha_256(data: bytes) -> tuple[str, str]:
    """SHA-256 hash of raw bytes (please use when possible).

    SHA-256 hash of raw bytes (please use when possible).

    Hash is computed directly from the raw bytes without any normalization.

    Returns a tuple of ``(hash, variant)`` where variant is ``"sha256+rawbytes"``.

    Raises :class:`TypeError` if *data* is not :class:`bytes`.
    """
    _check_type(data, bytes)

    hash_content = hashlib.sha256(data).hexdigest()
    hash_type = HASH_ALGORITHM_SHA_256 + HASH_CONNECTOR + HASH_VARIANT_BYTES

    return hash_content, hash_type


def hash_text_sha_256(text: str) -> tuple[str, str]:
    """SHA-256 hash of normalized text (please only use when rawbyte-hash not possible).

    Hashes over the output of :func:`normalise_volltext` so that minor
    formatting differences do not produce different hashes for semantically
    identical documents.

    Returns a tuple of ``(hash, variant)`` where variant is ``"sha256+text"``.

    Raises :class:`TypeError` if *text* is not :class:`str`.
    Raises :class:`ValueError` if the normalized text is empty (garbled or
        blank input).
    """
    _check_type(text, str)

    normalized = normalize_volltext(text)
    if not normalized:
        raise ValueError(
            "Cannot hash text: normalization produced an empty string "
            "(input is garbled or blank)"
        )
    hash_content = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    hash_type = HASH_ALGORITHM_SHA_256 + HASH_CONNECTOR + HASH_VARIANT_TEXT

    return hash_content, hash_type


# =====================================================================
# public comfort functions
# =====================================================================


def hash_text(text: str) -> tuple[str, str]:
    """Hash text with SHA-256, returning ``(digest, variant)``.

    Args:
        text (str): The input text to be hashed.

    Returns:
        tuple[str, str]: A tuple containing the binary hash and its hexadecimal
        representation.
    """
    return hash_text_sha_256(text)


def hash_bytes(data: bytes) -> list[tuple[str, str]]:
    """Computes hash values for the given byte data using multiple hashing algorithms.

    This function takes a byte sequence as input and calculates its hash values
    using two different hashing algorithms: SHA-1 (currently disabled, backend
    does not support it yet) and SHA-256. The results are
    returned as a list of tuples, where each tuple contains the name of the hashing
    algorithm and the corresponding hash value.

    Args:
        data: The input data as a sequence of bytes to be hashed.

    Returns:
        A list of tuples, where each tuple consists of:
            - The name of the hashing algorithm (str).
            - The hash value as a hexadecimal string (str).
    """
    result = list()
    # result.append(hash_bytes_sha_1(data)) (currently not supported by backend)
    result.append(hash_bytes_sha_256(data))

    return result
