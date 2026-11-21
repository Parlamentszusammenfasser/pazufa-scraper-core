"""Tests for the release script's version and file bumps."""

from __future__ import annotations

import datetime
import importlib.util
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = REPO_ROOT / "tools" / "release.py"

_spec = importlib.util.spec_from_file_location("release", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
next_version = _module.next_version
set_pyproject_version = _module.set_pyproject_version
bump_changelog = _module.bump_changelog


@pytest.mark.parametrize(
    ("current", "messages", "expected"),
    [
        ("0.3.5", ["fix: a", "docs: b"], "0.3.6"),
        ("0.3.5", ["feat(llm): a"], "0.3.6"),
        ("0.3.5", ["feat!: a"], "0.4.0"),
        ("0.3.5", ["fix: a\n\nBREAKING CHANGE: renamed X"], "0.4.0"),
        ("0.4.0rc1", ["fix: a"], "0.4.0"),
        ("1.2.3", ["fix: a"], "1.2.4"),
        ("1.2.3", ["fix: a", "feat: b"], "1.3.0"),
        ("1.2.3", ["refactor(cache)!: a"], "2.0.0"),
    ],
)
def test_next_version(current: str, messages: list[str], expected: str) -> None:
    assert next_version(current, messages) == expected


@pytest.mark.parametrize(("current", "messages"), [("0.3", ["fix: a"]), ("0.3.5", [])])
def test_next_version_refuses(current: str, messages: list[str]) -> None:
    with pytest.raises(ValueError):
        next_version(current, messages)


def test_set_pyproject_version_on_the_real_file() -> None:
    bumped = set_pyproject_version(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"), "9.8.7"
    )
    assert tomllib.loads(bumped)["project"]["version"] == "9.8.7"


def test_bump_changelog_moves_unreleased_entries() -> None:
    text = "# Changelog\n\n## [Unreleased]\n### Fixed\n- a bug\n\n## [0.3.5] - 19.11.2026\n- old\n"
    assert bump_changelog(text, "0.3.6", datetime.date(2026, 11, 21)) == (
        "# Changelog\n\n## [Unreleased]\n\n## [0.3.6] - 21.11.2026\n### Fixed\n- a bug\n\n"
        "## [0.3.5] - 19.11.2026\n- old\n"
    )


@pytest.mark.parametrize(
    "text",
    [
        "# Changelog\n\n## [Unreleased]\n\n## [0.3.5] - 19.11.2026\n- old\n",
        "# Changelog\n",
    ],
)
def test_bump_changelog_refuses_empty_or_missing_unreleased(text: str) -> None:
    with pytest.raises(ValueError):
        bump_changelog(text, "0.3.6", datetime.date(2026, 11, 21))
