"""Tests for the pip-audit wrapper and its ignore file."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = REPO_ROOT / "tools" / "run_pip_audit.py"

_spec = importlib.util.spec_from_file_location("run_pip_audit", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
load_ignored_cves = _module.load_ignored_cves
build_command = _module.build_command


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "ignore.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_repo_ignore_file_is_valid() -> None:
    assert load_ignored_cves()


def test_optional_fields_may_be_omitted(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "ignore:\n"
        "  - cve: CVE-2025-0001\n"
        "  - cve: CVE-2025-0002\n"
        "    notes: no fix yet\n"
        "    issue: https://codeberg.org/PaZuFa/pazufa-scraper-core/issues/1\n",
    )
    assert load_ignored_cves(path) == ["CVE-2025-0001", "CVE-2025-0002"]


def test_ghsa_and_pysec_ids_are_accepted(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "ignore:\n  - cve: GHSA-w596-4wvx-j9j6\n  - cve: PYSEC-2026-196\n",
    )
    assert load_ignored_cves(path) == ["GHSA-w596-4wvx-j9j6", "PYSEC-2026-196"]


def test_empty_file_ignores_nothing(tmp_path: Path) -> None:
    assert load_ignored_cves(_write(tmp_path, "")) == []


@pytest.mark.parametrize(
    "entry",
    [
        "  - notes: missing cve\n",
        "  - cve: GHSA-aaaa-bbbb-cccc\n",
        "  - cve: OSV-2026-1\n",
        "  - cve: cve-2025-0001\n",
        "  - cve: CVE-2025-0001\n    issue: not-a-url\n",
        "  - cve: CVE-2025-0001\n    reason: unknown field\n",
    ],
)
def test_invalid_entries_are_rejected(tmp_path: Path, entry: str) -> None:
    with pytest.raises(ValidationError):
        load_ignored_cves(_write(tmp_path, "ignore:\n" + entry))


def test_build_command_adds_one_flag_per_cve_and_passes_args_through() -> None:
    cmd = build_command(["CVE-2025-0001", "CVE-2025-0002"], ["--format", "json"])
    assert cmd == [
        sys.executable,
        "-m",
        "pip_audit",
        "--ignore-vuln",
        "CVE-2025-0001",
        "--ignore-vuln",
        "CVE-2025-0002",
        "--format",
        "json",
    ]
