from __future__ import annotations

import inspect
import json
import subprocess
import tempfile
import types
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import AnyHttpUrl, BaseModel
from pydantic.json_schema import models_json_schema

from pazufa_corelib import _api_model_hardening, api_model

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "pazufa_corelib" / "api_model_working.py"

CLASS_NAME_PREFIX = "Working"

# The mirror inherits the hardening base: blank strings become None and strings
# are stripped. `str_min_length=1` cannot bite here because every field is
# optional, so a blank is already None by the time the length check runs.
BASE_CLASS = "pazufa_corelib._api_model_hardening.PaZuFaBaseModel"

# Types that survive a JSON Schema roundtrip as something weaker (Sha256Hex ->
# str, TzDatetime -> AwareDatetime, AnyHttpUrl -> AnyUrl). They are restored
# through per-field `--type-overrides`, derived from the source annotations so
# there is no second list to keep in sync.
_PRESERVED_TYPES: tuple[tuple[Any, str], ...] = (
    (_api_model_hardening.Sha256Hex, "pazufa_corelib._api_model_hardening.Sha256Hex"),
    (_api_model_hardening.TzDatetime, "pazufa_corelib._api_model_hardening.TzDatetime"),
    (AnyHttpUrl, "pydantic.AnyHttpUrl"),
)

HEADER = f"""\
# GENERATED FILE - DO NOT EDIT.
# Regenerate with `make generate-working-models`; see
# tools/{Path(__file__).name}.
#
# Lenient mirror of pazufa_corelib.api_model: every field is optional so
# partially collected data can be carried around and type-checked before it is
# complete. Enums are reused from api_model and the models inherit the same
# hardening base, so members compare identical and blanks still become None.
#
# What is deliberately NOT reproduced: required fields, value constraints, and
# the @model_validator hooks. api_model stays the only place that decides
# whether an object is valid - hand it a `model_dump()` to find out.
"""

# Constraint keywords are dropped on purpose. They are what `api_model` enforces
# via PaZuFaBaseModel (`str_min_length=1`) and explicit Field bounds, and a
# working model must accept half-finished values. Dropping them also stops
# datamodel-codegen from emitting a named RootModel per constrained field.
_CONSTRAINT_KEYWORDS = frozenset(
    {
        "minLength",
        "maxLength",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)  # noqa: S603  # dev tool, command list is constructed in-repo


def _source_models() -> list[type[BaseModel]]:
    """Collect the models defined in `api_model`, in source order.

    Generic models are skipped: only their concrete parametrisations
    (`ReplacingEntry[Autor]` and friends) carry a JSON Schema, and those are
    pulled in as `$defs` by the models referencing them.
    """
    models: list[type[BaseModel]] = []
    for obj in vars(api_model).values():
        if not (inspect.isclass(obj) and issubclass(obj, BaseModel)):
            continue
        if obj.__module__ != api_model.__name__:
            continue
        if getattr(obj, "__pydantic_generic_metadata__", {}).get("parameters"):
            continue
        models.append(obj)
    return models


def _enum_overrides() -> dict[str, str]:
    """Map every enum in `api_model` onto its import path.

    Passed to datamodel-codegen as `--type-overrides`, which makes it import the
    handcrafted enum instead of emitting a copy.
    """
    return {
        name: f"{api_model.__name__}.{name}"
        for name, obj in vars(api_model).items()
        if inspect.isclass(obj)
        and issubclass(obj, Enum)
        and obj.__module__ == api_model.__name__
    }


def _sole_arm(annotation: Any) -> Any:
    """Return the only non-`None` arm of a union, or the annotation itself.

    `None` is returned when several real arms remain: an override replaces the
    *whole* field type, so it may only be applied when the custom type is the
    entire annotation. Overriding `list[AnyHttpUrl]` would silently turn the
    field into a bare `AnyHttpUrl`.
    """
    if get_origin(annotation) not in (Union, types.UnionType):
        return annotation
    arms = [arm for arm in get_args(annotation) if arm is not type(None)]
    return arms[0] if len(arms) == 1 else None


def _split_metadata(arm: Any, field_metadata: list[Any]) -> tuple[Any, list[Any]]:
    """Separate an annotation into its base type and its metadata.

    Pydantic keeps `Annotated` intact inside a union (`TzDatetime | None`) but
    flattens it into `FieldInfo.metadata` when it is wrapped in a `Field()`
    annotation, so both shapes have to be handled.
    """
    if get_origin(arm) is Annotated:
        base, *metadata = get_args(arm)
        return base, list(metadata)
    return arm, list(field_metadata)


def _preserved_type(annotation: Any, field_metadata: list[Any]) -> str | None:
    """Return the import path of the custom type this field uses, if any."""
    arm = _sole_arm(annotation)
    if arm is None:
        return None
    base, metadata = _split_metadata(arm, field_metadata)
    for alias, import_path in _PRESERVED_TYPES:
        if get_origin(alias) is Annotated:
            alias_base, *alias_metadata = get_args(alias)
            if base is alias_base and all(m in metadata for m in alias_metadata):
                return import_path
        elif base is alias:
            return import_path
    return None


def _scalar_overrides() -> dict[str, str]:
    """Map `WorkingModel.field` onto the custom type the source field uses."""
    overrides: dict[str, str] = {}
    for model in _source_models():
        for name, field in model.model_fields.items():
            import_path = _preserved_type(field.annotation, list(field.metadata))
            if import_path is not None:
                key = f"{CLASS_NAME_PREFIX}{model.__name__}.{name}"
                overrides[key] = import_path
    return overrides


def _strip(node: Any, *, keep_title: bool = False) -> None:
    """Remove auto-generated titles and constraints from a schema subtree."""
    if isinstance(node, dict):
        if not keep_title:
            node.pop("title", None)
        for keyword in _CONSTRAINT_KEYWORDS:
            node.pop(keyword, None)
        for key, value in node.items():
            if key != "$defs":
                _strip(value)
    elif isinstance(node, list):
        for value in node:
            _strip(value)


def _build_schema() -> dict[str, Any]:
    """Dump the handcrafted models as one JSON Schema document."""
    _, schema = models_json_schema(
        [(model, "validation") for model in _source_models()],
        ref_template="#/$defs/{model}",
    )
    for name, definition in schema["$defs"].items():
        _strip(definition, keep_title=True)
        if "properties" in definition:
            # Pydantic's per-field titles ("Expires At") are noise, but the title
            # on an object definition is what names the generated class.
            definition["title"] = name
        else:
            # Root-type definitions take their class name from the `$defs` key;
            # a title here would only resurface as `Field(title=...)`.
            definition.pop("title", None)
    return schema


def main() -> None:
    schema = _build_schema()
    overrides = _enum_overrides() | _scalar_overrides()
    with tempfile.TemporaryDirectory() as tmp:
        schema_file = Path(tmp) / "api_model.schema.json"
        schema_file.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        header_file = Path(tmp) / "header.txt"
        header_file.write_text(HEADER, encoding="utf-8")
        run(
            [
                "datamodel-codegen",
                "--input",
                str(schema_file),
                "--input-file-type",
                "jsonschema",
                "--output",
                str(DEST),
                "--force-optional",
                "--class-name-prefix",
                CLASS_NAME_PREFIX,
                "--class-name-affix-scope",
                "models",
                "--type-overrides",
                json.dumps(overrides),
                "--skip-root-model",
                "--base-class",
                BASE_CLASS,
                "--use-schema-description",
                "--custom-file-header-path",
                str(header_file),
                "--custom-file-header-mode",
                "prepend",
            ]
        )
    print(f"wrote {DEST.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
