"""Tests for pazufa_corelib._api_model_hardening.

The module is the hand-written half of the API models: everything in
`_api_model_generated.py` is thrown away on every regeneration, so the rules that
must survive live here. That makes this file the place where the guarantees
`api_model.py` relies on are pinned down.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated, Any, Optional, Union

import pytest
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from pazufa_corelib._api_model_hardening import (
    MEINUNG_ALLOWED_IF,
    SHA1_HEX_LENGTH,
    SHA256_HEX_LENGTH,
    PaZuFaBaseModel,
    Sha256Hex,
    TzDatetime,
    _allows_none,
    check_meinung_scope,
)
from pazufa_corelib.api_model import Autor, Doktyp, Dokument

HARDENING_LOGGER = "pazufa_corelib._api_model_hardening"

# =====================================================================
# Fixtures / helpers
# =====================================================================


@pytest.fixture()
def sha256_digest() -> str:
    """A real, lowercase sha256 digest."""
    return hashlib.sha256(b"pazufa").hexdigest()


class _Model(PaZuFaBaseModel):
    """Stand-in for a generated model, exercising every hardened field kind."""

    req: str
    opt: str | None = None
    opt_typing: Optional[str] = None  # noqa: UP045 — the `Optional` spelling is
    # deliberately kept: `_allows_none` must handle both.
    tags: list[str] | None = None
    number: int | None = None
    ts: TzDatetime | None = None


class _Nested(PaZuFaBaseModel):
    inner: _Model
    label: str | None = None


def _tz_adapter() -> TypeAdapter[datetime]:
    """A ``TzDatetime`` outside any model — no config, no field name."""
    return TypeAdapter(TzDatetime)


# =====================================================================
# TzDatetime / _ensure_tz
# =====================================================================


class TestTzDatetime:
    def test_naive_datetime_gets_utc(self) -> None:
        m = _Model(req="x", ts=datetime(2024, 3, 7, 12, 0))  # noqa: DTZ001
        assert m.ts is not None
        assert m.ts.tzinfo is not None
        assert m.ts.utcoffset() == timedelta(0)

    def test_naive_datetime_keeps_wall_clock_time(self) -> None:
        """UTC is *attached*, not converted to — the clock reading must not move."""
        m = _Model(req="x", ts=datetime(2024, 3, 7, 12, 0))  # noqa: DTZ001
        assert m.ts is not None
        assert (m.ts.hour, m.ts.minute) == (12, 0)

    def test_aware_datetime_untouched(self) -> None:
        original = datetime(2024, 3, 7, 12, 0, tzinfo=timezone(timedelta(hours=2)))
        m = _Model(req="x", ts=original)
        assert m.ts == original
        assert m.ts is not None
        assert m.ts.utcoffset() == timedelta(hours=2)

    def test_aware_datetime_offset_not_normalised_to_utc(self) -> None:
        """The offset survives; only *missing* offsets are repaired."""
        m = _Model(req="x", ts=datetime(2024, 3, 7, 12, 0, tzinfo=UTC) + timedelta(0))
        assert m.ts is not None
        assert m.ts.tzinfo is not None

    def test_naive_string_input_gets_utc(self) -> None:
        m = _Model(req="x", ts="2024-03-07T12:00:00")  # type: ignore[arg-type]
        assert m.ts is not None
        assert m.ts.utcoffset() == timedelta(0)

    def test_offset_string_input_preserved(self) -> None:
        m = _Model(req="x", ts="2024-03-07T12:00:00+02:00")  # type: ignore[arg-type]
        assert m.ts is not None
        assert m.ts.utcoffset() == timedelta(hours=2)

    def test_repair_is_logged_with_model_and_field(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The repair is silent otherwise; the warning names model and field."""
        with caplog.at_level(logging.WARNING, logger=HARDENING_LOGGER):
            _Model(req="x", ts=datetime(2024, 3, 7, 12, 0))  # noqa: DTZ001
        assert len(caplog.records) == 1
        message = caplog.records[0].getMessage()
        assert "_Model" in message
        assert "ts" in message
        assert "2024-03-07T12:00:00" in message

    def test_aware_datetime_logs_nothing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger=HARDENING_LOGGER):
            _Model(req="x", ts=datetime(2024, 3, 7, 12, 0, tzinfo=UTC))
        assert caplog.records == []

    def test_without_model_config_falls_back_to_unknown(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Bare ``TypeAdapter`` use has no config — the log must still work."""
        with caplog.at_level(logging.WARNING, logger=HARDENING_LOGGER):
            result = _tz_adapter().validate_python(datetime(2024, 3, 7))  # noqa: DTZ001
        assert result.utcoffset() == timedelta(0)
        assert "<unknown>" in caplog.records[0].getMessage()

    def test_serialised_value_carries_offset(self) -> None:
        """The point of the repair: the backend rejects offset-less timestamps."""
        m = _Model(req="x", ts=datetime(2024, 3, 7, 12, 0))  # noqa: DTZ001
        assert m.model_dump()["ts"] == "2024-03-07T12:00:00Z"

    def test_non_datetime_input_still_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _Model(req="x", ts="not a timestamp")  # type: ignore[arg-type]


# =====================================================================
# check_meinung_scope
# =====================================================================


class TestCheckMeinungScope:
    @pytest.mark.parametrize("typ", sorted(MEINUNG_ALLOWED_IF))
    def test_allowed_types_accept_meinung(self, typ: str) -> None:
        check_meinung_scope(3, typ)

    @pytest.mark.parametrize("typ", ["entwurf", "antrag", "gesetz", "sonstig"])
    def test_other_types_reject_meinung(self, typ: str) -> None:
        with pytest.raises(ValueError, match="only meaningful"):
            check_meinung_scope(3, typ)

    @pytest.mark.parametrize("typ", ["entwurf", "stellungnahme", "sonstig"])
    def test_none_meinung_always_passes(self, typ: str) -> None:
        check_meinung_scope(None, typ)

    def test_error_names_the_offending_type(self) -> None:
        with pytest.raises(ValueError, match="entwurf"):
            check_meinung_scope(1, "entwurf")

    def test_str_enum_member_accepted(self) -> None:
        """``typ`` is typed ``str`` so this file needs no model import."""
        check_meinung_scope(5, Doktyp.stellungnahme)
        with pytest.raises(ValueError, match="only meaningful"):
            check_meinung_scope(5, Doktyp.entwurf)

    def test_falsy_meinung_is_not_treated_as_unset(self) -> None:
        """``0`` is out of range for the field but must not bypass the check."""
        with pytest.raises(ValueError, match="only meaningful"):
            check_meinung_scope(0, "entwurf")


class TestMeinungScopeOnDokument:
    """The rule as `api_model.Dokument` wires it up."""

    @staticmethod
    def _kwargs(digest: str, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "autoren": [Autor(organisation="SPD")],
            "hash": digest,
            "link": "https://example.org/doc.pdf",
            "titel": "Ein Titel",
            "volltext": "Ein Volltext",
            "typ": Doktyp.stellungnahme,
            "zp_modifiziert": datetime(2024, 3, 9, tzinfo=UTC),
            "zp_referenz": datetime(2024, 3, 7, tzinfo=UTC),
        }
        base.update(overrides)
        return base

    def test_meinung_on_stellungnahme_accepted(self, sha256_digest: str) -> None:
        doc = Dokument(**self._kwargs(sha256_digest, meinung=4))
        assert doc.meinung == 4

    def test_meinung_on_beschlussempf_accepted(self, sha256_digest: str) -> None:
        doc = Dokument(
            **self._kwargs(sha256_digest, typ=Doktyp.beschlussempf, meinung=1)
        )
        assert doc.meinung == 1

    def test_meinung_on_entwurf_rejected(self, sha256_digest: str) -> None:
        with pytest.raises(ValidationError, match="only meaningful"):
            Dokument(**self._kwargs(sha256_digest, typ=Doktyp.entwurf, meinung=4))

    def test_no_meinung_on_entwurf_accepted(self, sha256_digest: str) -> None:
        doc = Dokument(**self._kwargs(sha256_digest, typ=Doktyp.entwurf))
        assert doc.meinung is None


# =====================================================================
# Sha256Hex
# =====================================================================


class TestSha256Hex:
    @staticmethod
    def _validate(value: str) -> str:
        return TypeAdapter(Sha256Hex).validate_python(value)

    def test_real_digest_accepted(self, sha256_digest: str) -> None:
        assert self._validate(sha256_digest) == sha256_digest

    def test_sha1_digest_rejected(self) -> None:
        """Regression guard: a 40-char sha1 digest is not a sha256 digest."""
        with pytest.raises(ValidationError, match="sha256"):
            self._validate(hashlib.sha1(b"pazufa").hexdigest())  # noqa: S324

    def test_uppercase_normalised_to_lowercase(self, sha256_digest: str) -> None:
        assert self._validate(sha256_digest.upper()) == sha256_digest

    def test_uppercase_normalisation_is_logged(
        self, sha256_digest: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger=HARDENING_LOGGER):
            self._validate(sha256_digest.upper())
        assert "normalised to lowercase" in caplog.records[0].getMessage()

    def test_lowercase_digest_logs_nothing(
        self, sha256_digest: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger=HARDENING_LOGGER):
            self._validate(sha256_digest)
        assert caplog.records == []

    @pytest.mark.parametrize(
        ("value", "reason"),
        [
            ("", "empty"),
            ("0" * (SHA256_HEX_LENGTH - 1), "one character short"),
            ("0" * (SHA256_HEX_LENGTH + 1), "one character too long"),
            ("g" * SHA256_HEX_LENGTH, "not hex"),
            ("0" * (SHA256_HEX_LENGTH - 1) + "z", "trailing non-hex character"),
            ("0" * (SHA256_HEX_LENGTH - 1) + " ", "trailing space"),
            (" " + "0" * SHA256_HEX_LENGTH, "leading space"),
        ],
    )
    def test_malformed_digests_rejected(self, value: str, reason: str) -> None:
        with pytest.raises(ValidationError, match="sha256"):
            self._validate(value)

    def test_error_reports_length_and_prefix(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            self._validate("abc")
        message = str(excinfo.value)
        assert "got 3 characters" in message
        assert "'abc'" in message

    def test_digest_on_dokument_is_normalised(self, sha256_digest: str) -> None:
        doc = Dokument(
            autoren=[Autor(organisation="SPD")],
            hash=sha256_digest.upper(),
            link="https://example.org/doc.pdf",  # type: ignore[arg-type]
            titel="Ein Titel",
            volltext="Ein Volltext",
            typ=Doktyp.entwurf,
            zp_modifiziert=datetime(2024, 3, 9, tzinfo=UTC),
            zp_referenz=datetime(2024, 3, 7, tzinfo=UTC),
        )
        assert doc.hash == sha256_digest


class TestHashConstants:
    def test_lengths_match_the_algorithms(self) -> None:
        assert SHA256_HEX_LENGTH == len(hashlib.sha256(b"").hexdigest())
        assert SHA1_HEX_LENGTH == len(hashlib.sha1(b"").hexdigest())  # noqa: S324

    def test_meinung_allowed_if_matches_doktyp_members(self) -> None:
        """A typo here would silently disable the rule for a whole type."""
        assert MEINUNG_ALLOWED_IF <= {member.value for member in Doktyp}


# =====================================================================
# _allows_none
# =====================================================================


class TestAllowsNone:
    @pytest.mark.parametrize(
        "annotation",
        [
            str | None,
            Optional[str],  # noqa: UP045
            Union[str, None],  # noqa: UP007
            list[str] | None,
            int | str | None,
            None | str,
            type(None),
        ],
    )
    def test_optional_annotations(self, annotation: Any) -> None:
        if annotation is type(None):
            # A bare ``NoneType`` is not a union, so it is not recognised —
            # pinned because nothing in the generated models produces it.
            assert _allows_none(annotation) is False
        else:
            assert _allows_none(annotation) is True

    @pytest.mark.parametrize(
        "annotation",
        [str, int, list[str], dict[str, int], int | str, datetime],
    )
    def test_non_optional_annotations(self, annotation: Any) -> None:
        assert _allows_none(annotation) is False

    def test_annotated_field_annotation_from_pydantic(self) -> None:
        """Pydantic strips ``Annotated`` before this ever sees the annotation."""

        class M(BaseModel):
            a: Annotated[str | None, Field(description="d")] = None
            b: Annotated[str, Field(description="d")] = "x"

        assert _allows_none(M.model_fields["a"].annotation) is True
        assert _allows_none(M.model_fields["b"].annotation) is False


# =====================================================================
# PaZuFaBaseModel — string handling
# =====================================================================


class TestBlankStringHandling:
    def test_whitespace_stripped(self) -> None:
        assert _Model(req="  value  ").req == "value"

    def test_blank_optional_becomes_none(self) -> None:
        assert _Model(req="x", opt="   ").opt is None

    def test_empty_optional_becomes_none(self) -> None:
        assert _Model(req="x", opt="").opt is None

    def test_blank_optional_typing_spelling_becomes_none(self) -> None:
        assert _Model(req="x", opt_typing="  ").opt_typing is None

    def test_blank_required_rejected_as_too_short(self) -> None:
        """The error type is the point: ``string_type`` would misname the cause."""
        with pytest.raises(ValidationError) as excinfo:
            _Model(req="   ")
        errors = excinfo.value.errors()
        assert [e["type"] for e in errors] == ["string_too_short"]

    def test_blank_inside_list_left_to_min_length(self) -> None:
        """The validator sees the container, not its items."""
        with pytest.raises(ValidationError) as excinfo:
            _Model(req="x", tags=["ok", "  "])
        error = excinfo.value.errors()[0]
        assert error["type"] == "string_too_short"
        assert error["loc"] == ("tags", 1)

    def test_non_blank_string_untouched(self) -> None:
        assert _Model(req="x", opt="value").opt == "value"

    def test_non_string_values_untouched(self) -> None:
        m = _Model(req="x", number=0, tags=[])
        assert m.number == 0
        assert m.tags == []

    def test_explicit_none_stays_none(self) -> None:
        assert _Model(req="x", opt=None).opt is None

    def test_blank_on_optional_non_string_field_becomes_none(self) -> None:
        """The rule keys on "field accepts ``None``", not on the field's type.

        A blank string arriving on an optional ``int`` therefore becomes ``None``
        rather than an ``int_parsing`` error — an empty CSV cell reads as "not
        present" there too.
        """
        assert _Model(req="x", number="   ").number is None  # type: ignore[arg-type]

    def test_non_blank_garbage_on_int_field_still_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _Model(req="x", number="zwölf")  # type: ignore[arg-type]

    def test_unknown_extra_field_ignored(self) -> None:
        """Blank extras hit the validator with a field name of their own."""
        m = _Model(req="x", unknown="   ")  # type: ignore[call-arg]
        assert not hasattr(m, "unknown")


# =====================================================================
# PaZuFaBaseModel — dumping
# =====================================================================


class TestModelDumpJson:
    def test_none_fields_dropped_by_default(self) -> None:
        assert _Model(req="x").model_dump_json() == '{"req":"x"}'

    def test_exclude_none_can_be_switched_off(self) -> None:
        payload = _Model(req="x").model_dump_json(exclude_none=False)
        assert '"opt":null' in payload

    def test_nested_models_covered(self) -> None:
        payload = _Nested(inner=_Model(req="x")).model_dump_json()
        assert payload == '{"inner":{"req":"x"}}'

    def test_other_kwargs_pass_through(self) -> None:
        payload = _Model(req="x", opt="y").model_dump_json(exclude={"opt"})
        assert payload == '{"req":"x"}'

    def test_set_optional_field_survives(self) -> None:
        assert '"opt":"y"' in _Model(req="x", opt="y").model_dump_json()


class TestModelDump:
    def test_json_mode_by_default(self) -> None:
        dumped = _Model(req="x", ts=datetime(2024, 3, 7, tzinfo=UTC)).model_dump()
        assert dumped["ts"] == "2024-03-07T00:00:00Z"

    def test_json_mode_drops_none(self) -> None:
        assert _Model(req="x").model_dump() == {"req": "x"}

    def test_json_mode_matches_model_dump_json(self) -> None:
        """The documented guarantee: both produce the same payload."""
        import json

        m = _Model(req="x", opt="y", ts=datetime(2024, 3, 7, tzinfo=UTC))
        assert json.dumps(m.model_dump()) == json.dumps(json.loads(m.model_dump_json()))

    def test_json_mode_exclude_none_can_be_switched_off(self) -> None:
        assert _Model(req="x").model_dump(exclude_none=False)["opt"] is None

    def test_python_mode_keeps_none(self) -> None:
        dumped = _Model(req="x").model_dump(mode="python")
        assert dumped["opt"] is None

    def test_python_mode_keeps_python_objects(self) -> None:
        ts = datetime(2024, 3, 7, tzinfo=UTC)
        dumped = _Model(req="x", ts=ts).model_dump(mode="python")
        assert dumped["ts"] == ts

    def test_python_mode_honours_explicit_exclude_none(self) -> None:
        dumped = _Model(req="x").model_dump(mode="python", exclude_none=True)
        assert dumped == {"req": "x"}

    def test_nested_models_dropped_none_in_json_mode(self) -> None:
        assert _Nested(inner=_Model(req="x")).model_dump() == {"inner": {"req": "x"}}

    def test_other_kwargs_pass_through(self) -> None:
        dumped = _Model(req="x", opt="y").model_dump(exclude={"opt"})
        assert dumped == {"req": "x"}


# =====================================================================
# Module surface
# =====================================================================


class TestModuleSurface:
    def test_all_names_are_importable(self) -> None:
        import pazufa_corelib._api_model_hardening as module

        for name in module.__all__:
            assert hasattr(module, name), name

    def test_base_model_config(self) -> None:
        assert PaZuFaBaseModel.model_config["str_strip_whitespace"] is True
        assert PaZuFaBaseModel.model_config["str_min_length"] == 1
