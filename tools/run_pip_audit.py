"""Run pip-audit with the ignore list from ``pip-audit-ignore.yaml``.

pip-audit only accepts ignores as repeated ``--ignore-vuln`` flags, so this
wrapper keeps the list in one file shared by ``make security`` and CI.
Extra arguments are passed through to pip-audit unchanged.

Usage::

    poetry run python -m tools.run_pip_audit
    poetry run python -m tools.run_pip_audit --format json
"""

import subprocess
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORE_FILE = REPO_ROOT / "pip-audit-ignore.yaml"

# The ID formats pip-audit documents for --ignore-vuln.
_VULN_ID_PATTERN = (
    r"^(CVE-\d{4}-\d{4,}"
    r"|GHSA(-[23456789cfghjmpqrvwx]{4}){3}"
    r"|PYSEC-\d{4}-\d+)$"
)


class IgnoredVulnerability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cve: str = Field(pattern=_VULN_ID_PATTERN)
    notes: str | None = None
    issue: HttpUrl | None = None


class IgnoreFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ignore: list[IgnoredVulnerability] = []


def load_ignored_cves(path: Path = IGNORE_FILE) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [entry.cve for entry in IgnoreFile.model_validate(data).ignore]


def build_command(ignored: list[str], extra_args: list[str]) -> list[str]:
    cmd = [sys.executable, "-m", "pip_audit"]
    for cve in ignored:
        cmd += ["--ignore-vuln", cve]
    return cmd + extra_args


def main() -> int:
    cmd = build_command(load_ignored_cves(), sys.argv[1:])
    return subprocess.run(cmd).returncode  # noqa: S603  # dev tool, command list is constructed in-repo


if __name__ == "__main__":
    sys.exit(main())
