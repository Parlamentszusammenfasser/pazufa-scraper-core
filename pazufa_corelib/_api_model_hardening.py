"""Additional hardening and expansion for api_model.py.

This file stores functions and classes to help in the Augmentatio of the in
'_api_model_generated.py' stored automatically generated pydantic models.

`api_model.py` imports from this file. To avoid circular imports, neber the
the inverse.
"""

import logging
import re
from datetime import UTC, datetime
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
)

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MEINUNG_ALLOWED_IF: frozenset[str] = frozenset({"stellungnahme", "beschlussempf"})
"""Documenttypes for wich a 'Meinung'-Value is reasonable."""
SHA256_HEX_LENGTH = 64
SHA1_HEX_LENGTH = 40

# ---------------------------------------------------------------------------
# RegEx
# ---------------------------------------------------------------------------
SHA256_HEX_RE = re.compile(rf"[0-9a-f]{{{SHA256_HEX_LENGTH}}}")
SHA1_HEX_RE = re.compile(rf"[0-9a-f]{{{SHA1_HEX_LENGTH}}}")

# ---------------------------------------------------------------------------
# Datetime
# ---------------------------------------------------------------------------


def _ensure_tz(value: datetime, info: ValidationInfo) -> datetime:
    """Attach UTC to naive datetimes so the offset survives serialisation.

    Logs a warning whenever it has to step in: the repair is silent otherwise,
    and a source that suddenly stops delivering offsets is worth noticing. The
    message names the model and field, which pydantic supplies via
    ``ValidationInfo``.

    Expect volume — for date-only sources every timestamp lands here. Silence it
    per logger if that is the normal case:
    ``logging.getLogger("pazufa_corelib._api_model_hardening").setLevel(ERROR)``.
    """
    if value.tzinfo is not None:
        return value
    model = info.config.get("title", "<unknown>") if info.config else "<unknown>"
    LOGGER.warning(
        "Naive datetime on %s.%s (%s); assuming UTC. The backend rejects "
        "timestamps without an offset.",
        model,
        info.field_name,
        value.isoformat(),
    )
    return value.replace(tzinfo=UTC)


TzDatetime = Annotated[datetime, AfterValidator(_ensure_tz)]
"""``datetime``, das immer zeitzonenbehaftet ist (naive Werte gelten als UTC).

Ersetzt in `api_model.py` jedes ``AwareDatetime`` der generierten Fassung: Der
generierte Typ *lehnt* naive Werte ab, dieser *repariert* sie.
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


# ---------------------------------------------------------------------------
# Hashes
# ---------------------------------------------------------------------------


def _check_sha256_hex(value: str, info: ValidationInfo) -> str:

    to_test = value.lower()
    if not SHA1_HEX_RE.fullmatch(to_test):
        raise ValueError(  # noqa: TRY003
            f"'hash' must be a hex-encoded sha256 digest "
            f"({SHA256_HEX_LENGTH} characters, 0-9a-f), "
            f"got {len(value)} characters: {value[:16]!r}"
        )

    if to_test != value:
        LOGGER.warning(
            "Uppercase digest on %s; normalised to lowercase.", info.field_name
        )

    return to_test


Sha256Hex = Annotated[str, AfterValidator(_check_sha256_hex)]
"""A hex encoded sha256 String always lowercase and 64 charachters."""

# ---------------------------------------------------------------------------
# PaZuFaBaseModel
# ---------------------------------------------------------------------------


def _allows_none(annotation: Any) -> bool:
    """Report whether a field annotation accepts ``None``.

    Covers both spellings of an optional field, ``str | None`` (``UnionType``)
    and ``Optional[str]`` (``typing.Union``). ``FieldInfo.annotation`` has the
    ``Annotated[...]`` metadata already stripped off by pydantic, so the
    ``Annotated[str | None, Field(...)]`` form used throughout `api_model.py`
    arrives here as a plain ``str | None``.
    """
    if get_origin(annotation) in (Union, UnionType) and type(None) in get_args(
        annotation
    ):
        return True
    else:
        return False


class PaZuFaBaseModel(BaseModel):
    """Child of pydantic BaseModel. With additional hardening for all PaZuFa Models.

    JSON is the intended export format for Objects inheriting from this class.
    For more information, see the wiki-page: https://migration.wiki.pazufa.de/link/165#bkmrk-page-title
    """

    model_config = ConfigDict(str_strip_whitespace=True, str_min_length=1)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any, info: ValidationInfo) -> Any:
        """Turn blank strings into ``None`` on optional fields.

        A field a source leaves empty means "not present", not "empty value".
        Mapping it to ``None`` lets :meth:`model_dump_json` drop it entirely
        instead of sending ``""`` to the backend.

        Only optional fields are converted. On a required field the blank string
        is passed through untouched so that ``str_min_length`` rejects it with
        ``string_too_short``; converting it would instead produce ``string_type``
        ("Input should be a valid string"), which points at the wrong cause.

        The raw value arrives here *before* ``str_strip_whitespace`` runs, so
        whitespace-only input has to be recognised here — hence ``.strip()``
        rather than a comparison against ``""``.

        Note this sees whole containers, not their items: an empty string inside
        a ``list[str]`` is left to ``str_min_length``.
        """
        if not isinstance(value, str) or value.strip():
            return value
        field = cls.model_fields.get(info.field_name or "")
        return None if field and _allows_none(field.annotation) else value

    def model_dump_json(self, **kw: Any) -> str:
        """Drop ``None`` fields by default.

        The backend distinguishes ``null`` from an absent key, and rejects the
        former on fields it considers unset. Keeping this at the call site meant
        every scraper had to remember ``exclude_none=True``; here it cannot be
        forgotten. The flag is passed down by pydantic-core through the whole
        tree, so nested models are covered too.
        """
        kw.setdefault("exclude_none", True)
        return super().model_dump_json(**kw)

    def model_dump(self, **kw: Any) -> dict[str, Any]:
        """Dump in JSON mode by default, so the result is JSON-serialisable.

        ``mode="json"`` turns ``UUID``, ``AnyHttpUrl`` and ``datetime`` into
        their string forms. In this mode ``exclude_none`` defaults on to match
        :meth:`model_dump_json`, so that ``json.dumps(m.model_dump())`` and
        ``m.model_dump_json()`` yield the same payload — without it, the former
        silently keeps the ``null`` values the backend rejects.

        Note that this changes the *types* in the returned dict: ``zp_start`` is
        a ``str``, not a ``datetime``. Callers that need the Python objects pass
        ``mode="python"`` explicitly. In that mode ``exclude_none`` is *not*
        forced — it falls back to pydantic's default (``False``), so ``None``
        fields are kept — because the python dump is meant for in-process use,
        not for building a backend payload. Pass ``exclude_none=True`` yourself
        if you want it dropped there too.
        """
        kw.setdefault("mode", "json")
        if kw["mode"] != "python":
            kw.setdefault("exclude_none", True)
        return super().model_dump(**kw)


__all__ = [
    "MEINUNG_ALLOWED_IF",
    "PaZuFaBaseModel",
    "TzDatetime",
    "check_meinung_scope",
    "Sha256Hex",
]
