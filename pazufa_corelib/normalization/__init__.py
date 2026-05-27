"""Text and date normalization utilities for parliamentary data."""

from pazufa_corelib.names_model import (
    AuthorIDResolution,
    NameIDResolution,
    OrganizationIDResolution,
)

from .hash import hash_bytes, hash_text
from .names import (
    AUTHORS_FILES,
    ORGANIZATIONS_FILES,
    AuthorResolver,
    OrganizationResolver,
    default_author_files,
    default_organization_files,
    normalize_name,
)
from .text import normalize_datum, normalize_name_key, normalize_volltext
from .urls import normalize_url

__all__ = [
    "AuthorIDResolution",
    "AuthorResolver",
    "default_author_files",
    "default_organization_files",
    "NameIDResolution",
    "OrganizationIDResolution",
    "OrganizationResolver",
    "hash_bytes",
    "hash_text",
    "normalize_datum",
    "normalize_name",
    "normalize_name_key",
    "normalize_url",
    "normalize_volltext",
    "AUTHORS_FILES",
    "ORGANIZATIONS_FILES",
]
