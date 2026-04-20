"""Tests for URL normalisation utilities."""

import pytest
from corelib.normalization.urls import normalise_url


class TestNormaliseUrl:
    def test_valid_http_url(self) -> None:
        assert normalise_url("http://example.com/") == "http://example.com/"

    def test_valid_https_url(self) -> None:
        assert normalise_url("https://example.com/") == "https://example.com/"

    def test_lowercases_scheme(self) -> None:
        assert normalise_url("HTTP://example.com/").startswith("http://")

    def test_lowercases_host(self) -> None:
        assert "example.com" in normalise_url("https://EXAMPLE.COM/path")

    def test_sorts_query_parameters(self) -> None:
        result = normalise_url("https://example.com/?z=1&a=2")
        assert result == "https://example.com/?a=2&z=1"

    def test_raises_for_ftp_scheme(self) -> None:
        with pytest.raises(ValueError, match="ftp"):
            normalise_url("ftp://example.com/file.txt")

    def test_raises_for_javascript_scheme(self) -> None:
        with pytest.raises(ValueError):
            normalise_url("javascript:alert(1)")

    def test_raises_for_empty_scheme(self) -> None:
        with pytest.raises(ValueError):
            normalise_url("//example.com/path")
