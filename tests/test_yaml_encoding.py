"""YAML loaders must read UTF-8 regardless of the platform's locale encoding."""

from pathlib import Path
from typing import Any

import pytest

from pazufa_corelib.names_model import AuthorFile, OrganizationFile
from pazufa_corelib.schlagworte_model import TagFile

AUTHOR_YAML = (
    "names:\n"
    "  - id: mueller-maria\n"
    "    canonical_name: Maria Müller\n"
    "    aliases:\n"
    "      - Dr. Maria Müller MdB\n"
)
ORGANIZATION_YAML = (
    "names:\n"
    "  - id: bmwk\n"
    "    canonical_name: Bundesministerium für Wirtschaft\n"
    "    acronym: BMWK\n"
    "    aliases: []\n"
)
TAG_YAML = "tags:\n  - id: Umwelt\n    description: Schutz der Gewässer und Böden\n"


@pytest.fixture()
def windows_default_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make Path.read_text default to cp1252, like Python on Windows."""
    original = Path.read_text

    def read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if not args and kwargs.get("encoding") is None:
            kwargs["encoding"] = "cp1252"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)


@pytest.mark.usefixtures("windows_default_encoding")
def test_author_file_reads_utf8(tmp_path: Path) -> None:
    path = tmp_path / "authors.yaml"
    path.write_text(AUTHOR_YAML, encoding="utf-8")

    author = AuthorFile.from_path(path).names[0]

    assert author.canonical_name == "Maria Müller"
    assert author.aliases == ["Dr. Maria Müller MdB"]


@pytest.mark.usefixtures("windows_default_encoding")
def test_organization_file_reads_utf8(tmp_path: Path) -> None:
    path = tmp_path / "orgs.yaml"
    path.write_text(ORGANIZATION_YAML, encoding="utf-8")

    org = OrganizationFile.from_path(path).names[0]

    assert org.canonical_name == "Bundesministerium für Wirtschaft"


@pytest.mark.usefixtures("windows_default_encoding")
def test_tag_file_reads_utf8(tmp_path: Path) -> None:
    path = tmp_path / "tags.yaml"
    path.write_text(TAG_YAML, encoding="utf-8")

    tag = TagFile.from_path(path).tags[0]

    assert tag.description == "Schutz der Gewässer und Böden"


@pytest.mark.parametrize(
    ("loader", "content"),
    [
        (AuthorFile.from_path, AUTHOR_YAML),
        (OrganizationFile.from_path, ORGANIZATION_YAML),
        (TagFile.from_path, TAG_YAML),
    ],
    ids=["author", "organization", "tag"],
)
def test_non_utf8_file_raises_value_error(
    tmp_path: Path, loader: Any, content: str
) -> None:
    path = tmp_path / "legacy.yaml"
    path.write_bytes(content.encode("cp1252"))

    with pytest.raises(ValueError, match="Failed to parse legacy.yaml"):
        loader(path)
