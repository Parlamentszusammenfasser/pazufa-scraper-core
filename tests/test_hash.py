"""Tests for hashing utilities."""

import hashlib

import pytest

from collector_core.normalization.hash import (
    HASH_VARIANT_BYTES,
    HASH_VARIANT_TEXT,
    hash_bytes,
    hash_text,
)
from collector_core.normalization.text import normalise_volltext


class TestHashBytes:
    def test_returns_tuple(self) -> None:
        result = hash_bytes(b"hello")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha256_hex(self) -> None:
        digest, _ = hash_bytes(b"hello")
        assert digest == hashlib.sha256(b"hello").hexdigest()

    def test_variant_is_correct(self) -> None:
        _, variant = hash_bytes(b"hello")
        assert variant == HASH_VARIANT_BYTES

    def test_empty_bytes(self) -> None:
        digest, variant = hash_bytes(b"")
        assert digest == hashlib.sha256(b"").hexdigest()
        assert variant == HASH_VARIANT_BYTES

    def test_different_inputs_produce_different_hashes(self) -> None:
        digest_a, _ = hash_bytes(b"foo")
        digest_b, _ = hash_bytes(b"bar")
        assert digest_a != digest_b

    def test_raises_type_error_for_str(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes("not bytes")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes(None)  # type: ignore[arg-type]


class TestHashText:
    def test_returns_tuple(self) -> None:
        result = hash_text("Hallo Welt")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha256_of_normalised_text(self) -> None:
        text = "Hallo Welt"
        digest, _ = hash_text(text)
        expected = hashlib.sha256(normalise_volltext(text).encode("utf-8")).hexdigest()
        assert digest == expected

    def test_variant_is_correct(self) -> None:
        _, variant = hash_text("Hallo Welt")
        assert variant == HASH_VARIANT_TEXT

    def test_empty_string(self) -> None:
        digest, variant = hash_text("")
        expected = hashlib.sha256(normalise_volltext("").encode("utf-8")).hexdigest()
        assert digest == expected
        assert variant == HASH_VARIANT_TEXT

    def test_different_inputs_produce_different_hashes(self) -> None:
        digest_a, _ = hash_text("foo")
        digest_b, _ = hash_text("bar")
        assert digest_a != digest_b

    def test_normalisation_produces_same_hash(self) -> None:
        # Minor formatting differences should yield the same hash
        digest_a, _ = hash_text("Hallo\r\nWelt")
        digest_b, _ = hash_text("Hallo\nWelt")
        assert digest_a == digest_b

    def test_raises_type_error_for_bytes(self) -> None:
        with pytest.raises(TypeError):
            hash_text(b"not a string")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_text(None)  # type: ignore[arg-type]
