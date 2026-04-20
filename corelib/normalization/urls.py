"""URL normalisation for parliamentary documents."""

from urllib.parse import urlparse

from w3lib.url import canonicalize_url


def normalise_url(url: str) -> str:
    """Normalise a URL to its canonical form.

    Canonicalises the URL using :func:`w3lib.url.canonicalize_url` (lowercased
    scheme and host, sorted query parameters, percent-encoding normalised).

    Raises :class:`ValueError` if *url* is not an http(s) URL.
    """
    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"None Valid URL scheme '{parsed.scheme}': only http und https are allowed."
        )

    return canonicalize_url(url)
