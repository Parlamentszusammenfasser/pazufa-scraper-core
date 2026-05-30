"""Experimental normalization utilities.

.. warning::
    Everything in this module is experimental and may be removed or changed
    without notice. Do not rely on it in production code.
"""

import logging
import warnings

from pazufa_corelib.api_model import Autor
from pazufa_corelib.normalization.authors import AuthorResolver
from pazufa_corelib.normalization.organizations import OrganizationResolver

LOGGER = logging.getLogger(__name__)


def normalize_autor(
    item: Autor,
    author_resolver: AuthorResolver,
    organization_resolver: OrganizationResolver,
) -> None:
    """Normalize the ``organisation`` and ``person`` fields of an Autor in-place.

    Resolves each field against the provided resolvers and updates it to the
    canonical name if a match is found; logs debug information otherwise.

    The original raw values are overwritten and not preserved. Callers that
    need the score, ID, or original string should use the resolvers directly.

    For batches of many ``Autor`` instances, calling this in a loop pays
    per-item matmul cost in :class:`OrganizationResolver`. Prefer
    :meth:`OrganizationResolver.resolve_batch` and write back manually.

    .. warning::
        Experimental — may be removed or changed without notice.

    Args:
        item: The Autor object whose fields are normalized in-place.
        author_resolver: Resolver used to normalize the ``person`` field.
        organization_resolver: Resolver used to normalize the
            ``organisation`` field.

    Raises:
        ValueError: If ``item.organisation`` is empty or whitespace-only.
    """
    warnings.warn(
        "normalize_autor is experimental and may be removed or changed without notice.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not item.organisation.strip():
        raise ValueError("Autor.organisation must be a non-empty string")
    org_resolution = organization_resolver.resolve(item.organisation)
    if org_resolution.score > 0:
        item.organisation = org_resolution.canonical_name
    else:
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "organization not resolvable",
                extra={"raw": item.organisation, "score": org_resolution.score},
            )

    if item.person is None or item.person.strip() == "":
        item.person = None
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("author person empty")
    else:
        # No error risen here, as an empty person is allowed.
        person_resolution = author_resolver.resolve(item.person)
        if person_resolution.score > 0:
            item.person = person_resolution.canonical_name
        else:
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug(
                    "author not resolvable",
                    extra={"raw": item.person, "score": person_resolution.score},
                )
