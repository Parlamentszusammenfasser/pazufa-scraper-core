"""
Additional hardening and expansion for api_model.py.

This file stores functions and classes to help in the Augmentatio of the in
'_api_model_generated.py' stored automatically generated pydantic models.

`api_model.py` imports from this file. To avoid circular imports, neber the
the inverse.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import AfterValidator, AnyHttpUrl, BeforeValidator
from pydantic.functional_serializers import PlainSerializer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MEINUNG_ALLOWED_IF: frozenset[str] = frozenset({"stellungnahme", "beschlussempf"})
"""Documenttypes for wich a 'Meinung'-Value is reasonable."""


# ---------------------------------------------------------------------------
# Datetime
# ---------------------------------------------------------------------------


def _ensure_tz(value: datetime) -> datetime:
    """
    Attach UTC to naive datetimes so the offset survives serialisation.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


TzDatetime = Annotated[datetime, AfterValidator(_ensure_tz)]
"""``datetime``, das immer zeitzonenbehaftet ist (naive Werte gelten als UTC).

Ersetzt in `api_model.py` jedes ``AwareDatetime`` der generierten Fassung: Der
generierte Typ *lehnt* naive Werte ab, dieser *repariert* sie.
"""


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

HttpUrlStr = Annotated[AnyHttpUrl, PlainSerializer(str, return_type=str)]
"""URL type that is serisabile. 

Important for model_dump() usage. When using model_dump_json() this is not critical.

This is needed when using the default export_feed of the Scrapy framework.
"""
# ---------------------------------------------------------------------------
# Thematic Rules
# ---------------------------------------------------------------------------


def check_meinung_scope(meinung: int | None, typ: str) -> None:
    """``meinung``  only makes sense for statements and recommended decisions.

    For all other document types, a set value is an error in the
    calling extraction, not data from the source. Called from a
    ``@model_validator(mode="after")`` in `api_model.py`; the rule is located here
    because it is domain knowledge and the specification is unaware of it.

    ``typ`` is accepted as a ``str`` (``StrEnum`` values fit directly),
    so that this file does not need to import any models.

    Raises:
        ValueError: if ``meinung`` is set for an unsuitable type.
    """

    if meinung is not None and str(typ) not in MEINUNG_ALLOWED_IF:
        raise ValueError(  # noqa: TRY003
            f"'Meinung' is only meaningful if type is  {sorted(MEINUNG_ALLOWED_IF)} , "
            f"not if type is '{typ}'"
        )


__all__ = [
    "MEINUNG_ALLOWED_IF",
    "HttpUrlStr",
    "TzDatetime",
    "check_meinung_scope",
]
