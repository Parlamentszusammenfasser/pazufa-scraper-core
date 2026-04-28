from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAPI = REPO_ROOT / "openapi.yaml"
CONFIG = Path(__file__).resolve().parent / "openapi-python-client.yaml"

GEN_PKG_NAME = "corelib_api_client"
DEST = REPO_ROOT / "corelib" / "api_client"

# openapi-python-client emits broken header code for these formats:
# - "date-time" produces `datetime | Unset` parameters that the client cannot
#   serialize back into a string.
# - "uuid" produces `UUID` parameters that get assigned directly to httpx's
#   headers dict, which rejects non-str values at request time.
# Body and query/path schemas keep their formats untouched.
_UNSUPPORTED_HEADER_FORMATS = {"date-time", "uuid"}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _patch_spec(spec: dict) -> dict:
    """Strip header formats that the Python client generator cannot honor.

    See ``_UNSUPPORTED_HEADER_FORMATS`` for the list and the reason. The
    source file on disk is never modified; this only operates on the loaded
    dict.
    """
    for path_item in spec.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                _strip_unsupported_header_format(param)
    for param in spec.get("components", {}).get("parameters", {}).values():
        _strip_unsupported_header_format(param)
    return spec


def _strip_unsupported_header_format(param: object) -> None:
    if not isinstance(param, dict):
        return
    if param.get("in") != "header":
        return
    schema = param.get("schema")
    if isinstance(schema, dict) and schema.get("format") in _UNSUPPORTED_HEADER_FORMATS:
        schema.pop("format")


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
