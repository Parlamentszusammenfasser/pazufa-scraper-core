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


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _patch_spec(spec: dict) -> dict:
    """Remove format: date-time from header parameters.

    openapi-python-client cannot handle datetime.datetime | Unset in headers,
    so we strip the format annotation before generation. The source file is
    never modified.
    """
    for path_item in spec.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if not isinstance(param, dict):
                    continue
                if param.get("in") == "header":
                    param.get("schema", {}).pop("format", None)
    for param in spec.get("components", {}).get("parameters", {}).values():
        if isinstance(param, dict) and param.get("in") == "header":
            param.get("schema", {}).pop("format", None)
    return spec


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="openapi-client-") as tmp:
        build_dir = Path(tmp)

        spec = yaml.safe_load(OPENAPI.read_text())
        patched_spec_path = build_dir / "openapi-patched.yaml"
        patched_spec_path.write_text(yaml.dump(_patch_spec(spec)))

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
