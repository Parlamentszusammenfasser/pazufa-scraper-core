"""Tests for hashing utilities."""

import hashlib

import pytest

from pazufa_corelib.normalization.hash import (
    HASH_ALGORITHM_SHA_1,
    HASH_ALGORITHM_SHA_256,
    HASH_CONNECTOR,
    HASH_VARIANT_BYTES,
    HASH_VARIANT_TEXT,
    hash_bytes,
    hash_bytes_sha_1,
    hash_bytes_sha_256,
    hash_text,
    hash_text_sha_256,
)
from pazufa_corelib.normalization.text import normalize_volltext

SHA1_BYTES_VARIANT = HASH_ALGORITHM_SHA_1 + HASH_CONNECTOR + HASH_VARIANT_BYTES
SHA256_BYTES_VARIANT = HASH_ALGORITHM_SHA_256 + HASH_CONNECTOR + HASH_VARIANT_BYTES
SHA256_TEXT_VARIANT = HASH_ALGORITHM_SHA_256 + HASH_CONNECTOR + HASH_VARIANT_TEXT


class TestHashBytesSha256:
    def test_returns_tuple(self) -> None:
        result = hash_bytes_sha_256(b"hello")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha256_hex(self) -> None:
        digest, _ = hash_bytes_sha_256(b"hello")
        assert digest == hashlib.sha256(b"hello").hexdigest()

    def test_variant_is_correct(self) -> None:
        _, variant = hash_bytes_sha_256(b"hello")
        assert variant == SHA256_BYTES_VARIANT

    def test_empty_bytes(self) -> None:
        digest, variant = hash_bytes_sha_256(b"")
        assert digest == hashlib.sha256(b"").hexdigest()
        assert variant == SHA256_BYTES_VARIANT

    def test_different_inputs_produce_different_hashes(self) -> None:
        digest_a, _ = hash_bytes_sha_256(b"foo")
        digest_b, _ = hash_bytes_sha_256(b"bar")
        assert digest_a != digest_b

    def test_raises_type_error_for_str(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes_sha_256("not bytes")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes_sha_256(None)  # type: ignore[arg-type]


class TestHashBytesSha1:
    def test_returns_tuple(self) -> None:
        result = hash_bytes_sha_1(b"hello")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha1_hex(self) -> None:
        digest, _ = hash_bytes_sha_1(b"hello")
        assert digest == hashlib.sha1(b"hello").hexdigest()

    def test_variant_is_correct(self) -> None:
        _, variant = hash_bytes_sha_1(b"hello")
        assert variant == SHA1_BYTES_VARIANT

    def test_empty_bytes(self) -> None:
        digest, variant = hash_bytes_sha_1(b"")
        assert digest == hashlib.sha1(b"").hexdigest()
        assert variant == SHA1_BYTES_VARIANT

    def test_different_inputs_produce_different_hashes(self) -> None:
        digest_a, _ = hash_bytes_sha_1(b"foo")
        digest_b, _ = hash_bytes_sha_1(b"bar")
        assert digest_a != digest_b

    def test_raises_type_error_for_str(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes_sha_1("not bytes")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes_sha_1(None)  # type: ignore[arg-type]


class TestHashTextSha256:
    def test_returns_tuple(self) -> None:
        result = hash_text_sha_256("Hallo Welt")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha256_of_normalized_text(self) -> None:
        text = "Hallo Welt"
        digest, _ = hash_text_sha_256(text)
        expected = hashlib.sha256(normalize_volltext(text).encode("utf-8")).hexdigest()
        assert digest == expected

    def test_variant_is_correct(self) -> None:
        _, variant = hash_text_sha_256("Hallo Welt")
        assert variant == SHA256_TEXT_VARIANT

    def test_empty_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="garbled or blank"):
            hash_text_sha_256("")

    def test_whitespace_only_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="garbled or blank"):
            hash_text_sha_256("   \n\t  ")

    def test_garbled_text_raises_value_error(self) -> None:
        # C1 control characters and Latin-Extended-B — triggers quality filter
        garbled = "\x80\x81\x82\x83\x84 \u0180\u0181\u0182\u0183\u0184"
        with pytest.raises(ValueError, match="garbled or blank"):
            hash_text_sha_256(garbled)

    def test_different_inputs_produce_different_hashes(self) -> None:
        digest_a, _ = hash_text_sha_256("foo")
        digest_b, _ = hash_text_sha_256("bar")
        assert digest_a != digest_b

    def test_normalisation_produces_same_hash(self) -> None:
        # Minor formatting differences must yield the same hash.
        digest_a, _ = hash_text_sha_256("Hallo\r\nWelt")
        digest_b, _ = hash_text_sha_256("Hallo\nWelt")
        assert digest_a == digest_b

    def test_raises_type_error_for_bytes(self) -> None:
        with pytest.raises(TypeError):
            hash_text_sha_256(b"not a string")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_text_sha_256(None)  # type: ignore[arg-type]


class TestHashBytes:
    """Tests for the hash_bytes comfort function."""

    def test_returns_list(self) -> None:
        result = hash_bytes(b"hello")
        assert isinstance(result, list)

    def test_each_entry_is_tuple_of_two_strings(self) -> None:
        for entry in hash_bytes(b"hello"):
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            digest, variant = entry
            assert isinstance(digest, str)
            assert isinstance(variant, str)

    def test_contains_sha256_entry(self) -> None:
        result = hash_bytes(b"hello")
        hashes = {variant: digest for digest, variant in result}
        assert SHA256_BYTES_VARIANT in hashes
        assert hashes[SHA256_BYTES_VARIANT] == hashlib.sha256(b"hello").hexdigest()

    def test_empty_bytes(self) -> None:
        hashes = {variant: digest for digest, variant in hash_bytes(b"")}
        assert hashes[SHA256_BYTES_VARIANT] == hashlib.sha256(b"").hexdigest()

    def test_different_inputs_produce_different_hashes(self) -> None:
        digests_a = {d for d, _ in hash_bytes(b"foo")}
        digests_b = {d for d, _ in hash_bytes(b"bar")}
        assert digests_a.isdisjoint(digests_b)

    def test_raises_type_error_for_str(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes("not bytes")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_bytes(None)  # type: ignore[arg-type]


class TestHashText:
    """Tests for the hash_text comfort function."""

    def test_delegates_to_hash_text_sha256(self) -> None:
        text = "Hallo Welt"
        assert hash_text(text) == hash_text_sha_256(text)

    def test_returns_tuple(self) -> None:
        result = hash_text("Hallo Welt")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha256_of_normalized_text(self) -> None:
        text = "Hallo Welt"
        digest, _ = hash_text(text)
        expected = hashlib.sha256(normalize_volltext(text).encode("utf-8")).hexdigest()
        assert digest == expected

    def test_variant_is_correct(self) -> None:
        _, variant = hash_text("Hallo Welt")
        assert variant == SHA256_TEXT_VARIANT

    def test_normalisation_produces_same_hash(self) -> None:
        digest_a, _ = hash_text("Hallo\r\nWelt")
        digest_b, _ = hash_text("Hallo\nWelt")
        assert digest_a == digest_b

    def test_raises_type_error_for_bytes(self) -> None:
        with pytest.raises(TypeError):
            hash_text(b"not a string")  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError):
            hash_text(None)  # type: ignore[arg-type]
