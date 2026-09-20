from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAPI = REPO_ROOT / "openapi.yaml"
CONFIG = Path(__file__).resolve().parent / "openapi-python-client.yaml"

# Jinja templates that override the generator's own. Only files present here are
# replaced; everything else still comes from the installed package. Currently
# just `types.py.jinja`, which adds a `__repr__` to `Unset` so `UNSET` prints as
# "UNSET" instead of an object address in logs and reprs of generated models.
# See `test_types_template_matches_upstream` for the drift guard.
TEMPLATES = Path(__file__).resolve().parent / "openapi_templates"

GEN_PKG_NAME = "pazufa_corelib_api_client"
DEST = REPO_ROOT / "pazufa_corelib" / "api_client"

# openapi-python-client emits broken header code for these formats:
# - "date-time" produces `datetime | Unset` parameters that the client cannot
#   serialize back into a string.
# - "uuid" produces `UUID` parameters that get assigned directly to httpx's
#   headers dict, which rejects non-str values at request time.
# Body and query/path schemas keep their formats untouched.
_UNSUPPORTED_HEADER_FORMATS = {"date-time", "uuid"}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)  # noqa: S603  # dev tool, command list is constructed in-repo


def _patch_spec(spec: dict) -> dict:
    """Normalise upstream spec constructs the Python client generator rejects.

    Three fixes, all confined to the loaded dict — the source file on disk is
    never modified:

    1. Header ``format`` values the generator mis-renders. See
       ``_UNSUPPORTED_HEADER_FORMATS``.
    2. Query parameters mislabelled ``in: path`` (see
       ``_relocate_phantom_path_params``).
    3. Object-typed header parameters (see ``_unwrap_object_header``).

    Fixes 2 and 3 target constructs that are *invalid* OpenAPI rather than
    merely awkward: without them the generator drops the whole endpoint. Only
    provably-unusable declarations are rewritten here; changes that are valid
    OpenAPI but semantically surprising are deliberately mirrored as-is so the
    generated client stays a faithful image of the tagged spec.
    """
    for path, path_item in spec.get("paths", {}).items():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            _relocate_phantom_path_params(path, operation)
            for param in operation.get("parameters", []):
                if isinstance(param, dict):
                    _strip_unsupported_header_format(param)
                    _unwrap_object_header(spec, param)
    for param in spec.get("components", {}).get("parameters", {}).values():
        if isinstance(param, dict):
            _strip_unsupported_header_format(param)
            _unwrap_object_header(spec, param)
    return spec


def _strip_unsupported_header_format(param: dict[str, Any]) -> None:
    if param.get("in") != "header":
        return
    schema = param.get("schema")
    if isinstance(schema, dict) and schema.get("format") in _UNSUPPORTED_HEADER_FORMATS:
        schema.pop("format")


def _relocate_phantom_path_params(path: str, operation: dict[str, Any]) -> None:
    """Move ``in: path`` parameters that the path template never declares to query.

    Spec 0.2.5 marks the ``GET /api/v2/autoren`` filters (``person``, ``fach``,
    ``org``, ``page``, ``per_page``) as ``in: path``, but ``/api/v2/autoren``
    has no ``{...}`` placeholders at all — so no request could ever bind them.
    They were ``in: query, required: false`` in 0.2.3 and are described as
    filters, so this is an upstream generation artifact. Left alone, the
    generator refuses the endpoint outright and ``autoren_get`` disappears
    from the client.

    ``required`` is dropped alongside the move: a filter typed ``[string,
    null]`` is optional by construction, and a required query parameter would
    force callers to pass every filter on every call.
    """
    for param in operation.get("parameters", []):
        if not isinstance(param, dict) or param.get("in") != "path":
            continue
        if "{" + str(param.get("name")) + "}" in path:
            continue
        param["in"] = "query"
        param["required"] = False


def _unwrap_object_header(spec: dict[str, Any], param: dict[str, Any]) -> None:
    """Replace an object-typed header schema with its single scalar property.

    Spec 0.2.5 types the ``api-key-delete`` header of ``DELETE /api/v2/auth``
    as ``$ref: AuthDeleteHeaderParams``, an object wrapping one string field.
    An HTTP header carries a scalar, and 0.2.3 typed this same header as a
    plain string, so the wrapper is an upstream generation artifact. Left
    alone, the generator refuses the endpoint and ``auth_delete`` disappears
    from the client.

    Only single-property objects are unwrapped; anything else is left for a
    human to look at.
    """
    if param.get("in") != "header":
        return
    schema = param.get("schema")
    if not isinstance(schema, dict):
        return
    ref = schema.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/components/schemas/"):
        return
    target = spec.get("components", {}).get("schemas", {}).get(ref.rsplit("/", 1)[-1])
    if not isinstance(target, dict) or target.get("type") != "object":
        return
    properties = target.get("properties")
    if not isinstance(properties, dict) or len(properties) != 1:
        return
    (inner,) = properties.values()
    if isinstance(inner, dict):
        param["schema"] = dict(inner)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="openapi-client-") as tmp:
        build_dir = Path(tmp)

        spec = yaml.safe_load(OPENAPI.read_text())
        patched_spec_path = build_dir / "openapi-patched.yaml"
        patched_spec_path.write_text(yaml.dump(_patch_spec(spec), sort_keys=False))

        run(
            [
                "poetry",
                "run",
                "openapi-python-client",
                "generate",
                "--path",
                str(patched_spec_path),
                "--config",
                str(CONFIG),
                "--custom-template-path",
                str(TEMPLATES),
                "--output-path",
                str(build_dir),
                "--overwrite",
            ]
        )

        src_pkg = build_dir / GEN_PKG_NAME
        if not src_pkg.exists():
            raise RuntimeError(f"Generated package not found: {src_pkg}")

        if DEST.exists():
            shutil.rmtree(DEST)
        shutil.copytree(src_pkg, DEST)

    run(["poetry", "run", "ruff", "check", "--select", "I", "--fix", str(DEST)])
    run(["poetry", "run", "ruff", "format", str(DEST)])


if __name__ == "__main__":
    main()
