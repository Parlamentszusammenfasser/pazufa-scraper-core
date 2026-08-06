"""Parity checks between api_model and its generated all-optional mirror.

These guard the risk that comes with checking a generated file into the repo:
`api_model.py` gets edited and nobody runs `make generate-working-models`.
"""

from __future__ import annotations

import inspect
from enum import Enum

import pytest
from pydantic import BaseModel

from pazufa_corelib import api_model, api_model_working


def _source_models() -> list[type[BaseModel]]:
    return [
        obj
        for obj in vars(api_model).values()
        if inspect.isclass(obj)
        and issubclass(obj, BaseModel)
        and obj.__module__ == api_model.__name__
        and not getattr(obj, "__pydantic_generic_metadata__", {}).get("parameters")
    ]


def _source_enums() -> list[type[Enum]]:
    return [
        obj
        for obj in vars(api_model).values()
        if inspect.isclass(obj)
        and issubclass(obj, Enum)
        and obj.__module__ == api_model.__name__
    ]


@pytest.mark.parametrize("model", _source_models(), ids=lambda m: m.__name__)
def test_working_counterpart_exists(model: type[BaseModel]) -> None:
    assert hasattr(api_model_working, f"Working{model.__name__}")


@pytest.mark.parametrize("model", _source_models(), ids=lambda m: m.__name__)
def test_field_names_match(model: type[BaseModel]) -> None:
    working = getattr(api_model_working, f"Working{model.__name__}")
    assert set(working.model_fields) == set(model.model_fields)


@pytest.mark.parametrize("model", _source_models(), ids=lambda m: m.__name__)
def test_every_field_is_optional(model: type[BaseModel]) -> None:
    working = getattr(api_model_working, f"Working{model.__name__}")
    working()  # constructing without arguments must not raise
    for name, field in working.model_fields.items():
        assert not field.is_required(), f"{working.__name__}.{name} is required"
        assert field.default is None, f"{working.__name__}.{name} defaults to non-None"


@pytest.mark.parametrize("enum", _source_enums(), ids=lambda e: e.__name__)
def test_enums_are_reused_not_copied(enum: type[Enum]) -> None:
    """The mirror must import the handcrafted enums, never redefine them."""
    imported = getattr(api_model_working, enum.__name__, None)
    if imported is None:
        # Not referenced by any model, so it is never imported into the mirror.
        return
    assert imported is enum
