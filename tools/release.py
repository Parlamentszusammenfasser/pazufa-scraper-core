"""Cut a release on main: pick the version, bump files, commit and tag.

Run by the manual ``release`` step in ``.woodpecker.yml``, which then pushes
the commit and the tag; the tag pipeline publishes to (Test)PyPI.

``RELEASE_VERSION`` (env) sets the version, e.g. ``0.4.0`` or ``0.4.0rc1``.
Without it the version is bumped from the conventional commits since the last
tag: before 1.0 a breaking change bumps the minor version and everything else
the patch version; from 1.0 on breaking -> major, ``feat`` -> minor, else patch.
An rc in ``pyproject.toml`` is finalised (``0.4.0rc1`` -> ``0.4.0``).

Final releases turn ``## [Unreleased]`` in CHANGELOG.md into the version's
section and refuse to run if it is empty; rc releases leave CHANGELOG.md alone.
"""

import datetime
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Only the forms the publish steps accept: X.Y.Z (PyPI) and X.Y.ZrcN (TestPyPI).
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(rc\d+)?$")
_BREAKING_RE = re.compile(r"^\w+(\([^)]*\))?!:|^BREAKING[ -]CHANGE:", re.MULTILINE)
_FEAT_RE = re.compile(r"^feat(\([^)]*\))?:")
_PYPROJECT_VERSION_RE = re.compile(r'^version = "[^"]*"$', re.MULTILINE)
_UNRELEASED = "## [Unreleased]\n"


def next_version(current: str, messages: list[str]) -> str:
    match = VERSION_RE.match(current)
    if not match:
        raise ValueError(f"pyproject.toml version {current!r} is not X.Y.Z or X.Y.ZrcN")
    major, minor, patch = (int(part) for part in match.groups()[:3])
    if match.group(4):
        return f"{major}.{minor}.{patch}"
    if not messages:
        raise ValueError("no commits since the last tag")
    breaking = any(_BREAKING_RE.search(message) for message in messages)
    feat = any(_FEAT_RE.match(message) for message in messages)
    if breaking and major == 0:
        return f"0.{minor + 1}.0"
    if breaking:
        return f"{major + 1}.0.0"
    if feat and major > 0:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def set_pyproject_version(text: str, version: str) -> str:
    new, count = _PYPROJECT_VERSION_RE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise ValueError("no 'version = \"...\"' line in pyproject.toml")
    return new


def bump_changelog(text: str, version: str, date: datetime.date) -> str:
    head, heading, rest = text.partition(_UNRELEASED)
    if not heading:
        raise ValueError("CHANGELOG.md has no '## [Unreleased]' heading")
    if not re.split(r"^## ", rest, maxsplit=1, flags=re.MULTILINE)[0].strip():
        raise ValueError("CHANGELOG.md has nothing under [Unreleased]")
    return f"{head}{heading}\n## [{version}] - {date:%d.%m.%Y}\n{rest}"


def _git(*args: str) -> str:
    result = subprocess.run(  # noqa: S603  # command list is constructed in-repo
        ["git", *args],  # noqa: S607  # git from PATH, as in CI
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit_messages_since_last_tag() -> list[str]:
    try:
        last_tag = _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
        revisions = f"{last_tag}..HEAD"
    except subprocess.CalledProcessError:  # no tag yet
        revisions = "HEAD"
    log = _git("log", "--format=%B%x00", revisions)
    return [message.strip() for message in log.split("\0") if message.strip()]


def main() -> None:
    current = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    version = os.environ.get("RELEASE_VERSION", "").strip()
    try:
        if not version:
            version = next_version(current, _commit_messages_since_last_tag())
        elif not VERSION_RE.match(version):
            raise ValueError(f"RELEASE_VERSION {version!r} is not X.Y.Z or X.Y.ZrcN")
        if _git("tag", "--list", f"v{version}"):
            raise ValueError(f"v{version} is already tagged")
        # Build both files before writing either, so a refusal changes nothing.
        pyproject = set_pyproject_version(
            PYPROJECT.read_text(encoding="utf-8"), version
        )
        changelog = CHANGELOG.read_text(encoding="utf-8")
        if "rc" not in version:
            today = datetime.datetime.now(datetime.UTC).date()
            changelog = bump_changelog(changelog, version, today)
    except ValueError as error:
        sys.exit(f"ERROR: {error}")
    PYPROJECT.write_text(pyproject, encoding="utf-8")
    CHANGELOG.write_text(changelog, encoding="utf-8")

    identity = ["-c", "user.name=PaZuFa Release", "-c", "user.email=pub@pazufa.de"]
    _git(*identity, "commit", "--all", "--message", f"chore(release): v{version}")
    _git(*identity, "tag", "--annotate", f"v{version}", "--message", f"v{version}")
    print(f"Prepared v{version} ({current} -> {version})")


if __name__ == "__main__":
    main()
