"""Tests for the OpenAPI client generation helpers."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = REPO_ROOT / "tools" / "generate_openapi_client.py"

_spec = importlib.util.spec_from_file_location("generate_openapi_client", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
_patch_spec = _module._patch_spec


def _sample_spec() -> dict[str, Any]:
    return {
        "paths": {
            "/api/v2/vorgang/{vorgang_id}": {
                "get": {
                    "parameters": [
                        {
                            "name": "vorgang_id",
                            "in": "path",
                            "schema": {"type": "string", "format": "uuid"},
                        },
                        {
                            "name": "since",
                            "in": "query",
                            "schema": {"type": "string", "format": "date-time"},
                        },
                        {
                            "name": "If-Modified-Since",
                            "in": "header",
                            "schema": {"type": "string", "format": "date-time"},
                        },
                        {
                            "name": "X-Scraper-Id",
                            "in": "header",
                            "schema": {"type": "string", "format": "uuid"},
                        },
                        {
                            "name": "X-Custom",
                            "in": "header",
                            "schema": {"type": "string", "format": "byte"},
                        },
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "string", "format": "date-time"},
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "parameters": {
                "if-mod-since": {
                    "name": "If-Modified-Since",
                    "in": "header",
                    "schema": {"type": "string", "format": "date-time"},
                },
                "scraper-id": {
                    "name": "X-Scraper-Id",
                    "in": "header",
                    "schema": {"type": "string", "format": "uuid"},
                },
                "updated-since": {
                    "name": "since",
                    "in": "query",
                    "schema": {"type": "string", "format": "date-time"},
                },
            }
        },
    }


def test_strips_date_time_format_from_inline_header() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    params = patched["paths"]["/api/v2/vorgang/{vorgang_id}"]["get"]["parameters"]
    if_mod = next(p for p in params if p["name"] == "If-Modified-Since")
    assert "format" not in if_mod["schema"]


def test_strips_date_time_format_from_component_header() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    if_mod = patched["components"]["parameters"]["if-mod-since"]
    assert "format" not in if_mod["schema"]


def test_strips_uuid_format_from_inline_header() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    params = patched["paths"]["/api/v2/vorgang/{vorgang_id}"]["get"]["parameters"]
    scraper_id = next(p for p in params if p["name"] == "X-Scraper-Id")
    assert "format" not in scraper_id["schema"]


def test_strips_uuid_format_from_component_header() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    scraper_id = patched["components"]["parameters"]["scraper-id"]
    assert "format" not in scraper_id["schema"]


def test_leaves_other_header_formats_untouched() -> None:
    """Only the formats the generator can't handle are stripped."""
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    params = patched["paths"]["/api/v2/vorgang/{vorgang_id}"]["get"]["parameters"]
    custom = next(p for p in params if p["name"] == "X-Custom")
    assert custom["schema"]["format"] == "byte"


def test_preserves_uuid_format_on_path_parameter() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    params = patched["paths"]["/api/v2/vorgang/{vorgang_id}"]["get"]["parameters"]
    vorgang_id = next(p for p in params if p["name"] == "vorgang_id")
    assert vorgang_id["schema"]["format"] == "uuid"


def test_preserves_date_time_format_on_query_parameter() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    params = patched["paths"]["/api/v2/vorgang/{vorgang_id}"]["get"]["parameters"]
    since_inline = next(p for p in params if p["name"] == "since")
    assert since_inline["schema"]["format"] == "date-time"

    since_component = patched["components"]["parameters"]["updated-since"]
    assert since_component["schema"]["format"] == "date-time"


def test_preserves_format_on_request_body() -> None:
    spec = _sample_spec()
    patched = _patch_spec(copy.deepcopy(spec))

    body_schema = patched["paths"]["/api/v2/vorgang/{vorgang_id}"]["get"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    assert body_schema["format"] == "date-time"


def _real_spec() -> dict[str, Any]:
    spec: dict[str, Any] = yaml.safe_load((REPO_ROOT / "openapi.yaml").read_text())
    return spec


def _header_params(spec: dict[str, Any]) -> dict[str, str | None]:
    """Return ``{header_name: format-or-None}`` over the entire spec."""
    out: dict[str, str | None] = {}
    for path_item in spec.get("paths", {}).values():
        for op in path_item.values():
            if not isinstance(op, dict):
                continue
            for p in op.get("parameters", []):
                if isinstance(p, dict) and p.get("in") == "header":
                    out[p["name"]] = p.get("schema", {}).get("format")
    for p in spec.get("components", {}).get("parameters", {}).values():
        if isinstance(p, dict) and p.get("in") == "header":
            out[p["name"]] = p.get("schema", {}).get("format")
    return out


def test_patch_spec_against_real_openapi_yaml() -> None:
    """Sanity check on the real spec, not just the synthetic fixture."""
    spec = _real_spec()
    before = _header_params(spec)
    assert before.get("If-Modified-Since") == "date-time", (
        "Precondition: spec should still declare If-Modified-Since as date-time"
    )
    assert before.get("X-Scraper-Id") == "uuid", (
        "Precondition: spec should still declare X-Scraper-Id as uuid"
    )

    patched = _patch_spec(copy.deepcopy(spec))
    after = _header_params(patched)
    assert after["If-Modified-Since"] is None
    assert after["X-Scraper-Id"] is None
