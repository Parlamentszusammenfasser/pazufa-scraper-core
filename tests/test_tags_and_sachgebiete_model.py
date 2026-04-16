"""Tests for collector_core.schlagworte_model."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from collector_core.schlagworte_model import (
    Sachgebiet,
    SachgebietFile,
    SchlagwortIDResolution,
    Tag,
    TagFile,
)

# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture()
def tag_yaml_file(tmp_path: Path) -> Path:
    """A minimal, valid Tag YAML file."""
    f = tmp_path / "tags.yaml"
    f.write_text(
        "tags:\n"
        "  - id: Digitalisierung\n"
        "    description: Digitale Infrastruktur\n"
        "  - id: Wohnungsbau\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def sachgebiet_yaml_file(tmp_path: Path) -> Path:
    """A minimal, valid Sachgebiet YAML file."""
    f = tmp_path / "sachgebiete.yaml"
    f.write_text(
        "tags:\n"
        "  - id: Umwelt\n"
        "    number: 100\n"
        "    description: Umweltschutz\n"
        "  - id: Bildung\n"
        "    number: 200\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def source_file(tmp_path: Path) -> Path:
    """An existing, empty file usable as a model `source` path."""
    f = tmp_path / "source.yaml"
    f.touch()
    return f


# =====================================================================
# Tag — ID validation
# =====================================================================


class TestTagIdValidation:
    @pytest.mark.parametrize(
        "valid_id",
        [
            "Umwelt",
            "Öffentlichkeit",
            "Straßenrecht",
            "Baden-Württemberg",
            "Soziale Sicherheit",
        ],
    )
    def test_valid_ids_are_accepted(self, valid_id: str) -> None:
        assert Tag(id=valid_id).id == valid_id

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "Tag1",  # digit
            "Tag!",  # special char
            "Tag@Schlagwort",  # @ symbol
            "A",  # single character (regex requires ≥2 chars)
            "",  # empty string
        ],
    )
    def test_invalid_ids_raise_validation_error(self, invalid_id: str) -> None:
        with pytest.raises(ValidationError):
            Tag(id=invalid_id)

    def test_description_defaults_to_none(self) -> None:
        assert Tag(id="Umwelt").description is None

    def test_description_can_be_set(self) -> None:
        tag = Tag(id="Umwelt", description="Umweltschutz")
        assert tag.description == "Umweltschutz"


# =====================================================================
# Sachgebiet
# =====================================================================


class TestSachgebiet:
    def test_valid_sachgebiet(self) -> None:
        s = Sachgebiet(id="Umwelt", number=1)
        assert s.id == "Umwelt"
        assert s.number == 1

    def test_description_optional(self) -> None:
        assert Sachgebiet(id="Umwelt", number=1).description is None

    def test_description_can_be_set(self) -> None:
        s = Sachgebiet(id="Umwelt", number=1, description="Natur")
        assert s.description == "Natur"

    @pytest.mark.parametrize("bad_number", [0, -1, -100])
    def test_non_positive_number_raises(self, bad_number: int) -> None:
        with pytest.raises(ValidationError):
            Sachgebiet(id="Umwelt", number=bad_number)

    def test_inherits_id_validation(self) -> None:
        with pytest.raises(ValidationError):
            Sachgebiet(id="Tag1", number=1)


# =====================================================================
# TagFile — construction and validation
# =====================================================================


class TestTagFile:
    def test_valid_file_with_multiple_tags(self, source_file: Path) -> None:
        tf = TagFile(source=source_file, tags=[Tag(id="Umwelt"), Tag(id="Bildung")])
        assert len(tf.tags) == 2

    def test_empty_tags_list_is_allowed(self, source_file: Path) -> None:
        assert TagFile(source=source_file, tags=[]).tags == []

    def test_duplicate_ids_raise(self, source_file: Path) -> None:
        with pytest.raises(ValidationError, match="Duplicate IDs"):
            TagFile(source=source_file, tags=[Tag(id="Umwelt"), Tag(id="Umwelt")])

    def test_nonexistent_source_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            TagFile(source=tmp_path / "missing.yaml", tags=[])


# =====================================================================
# TagFile.from_path
# =====================================================================


class TestTagFileFromPath:
    def test_loads_valid_yaml(self, tag_yaml_file: Path) -> None:
        tf = TagFile.from_path(tag_yaml_file)
        ids = {t.id for t in tf.tags}
        assert ids == {"Digitalisierung", "Wohnungsbau"}

    def test_description_is_parsed(self, tag_yaml_file: Path) -> None:
        tf = TagFile.from_path(tag_yaml_file)
        tag = next(t for t in tf.tags if t.id == "Digitalisierung")
        assert tag.description == "Digitale Infrastruktur"

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            TagFile.from_path(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises_value_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("tags: [invalid: yaml: :\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Failed to parse"):
            TagFile.from_path(bad)

    def test_validation_failure_raises_value_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("tags:\n  - id: Tag1\n", encoding="utf-8")  # digit in id
        with pytest.raises(ValueError, match="Validation failed"):
            TagFile.from_path(bad)


# =====================================================================
# SachgebietFile — construction and validation
# =====================================================================


class TestSachgebietFile:
    def test_valid_file_with_multiple_sachgebiete(self, source_file: Path) -> None:
        sf = SachgebietFile(
            source=source_file,
            tags=[
                Sachgebiet(id="Umwelt", number=1),
                Sachgebiet(id="Bildung", number=2),
            ],
        )
        assert len(sf.tags) == 2

    def test_duplicate_ids_raise(self, source_file: Path) -> None:
        with pytest.raises(ValidationError, match="Duplicate IDs"):
            SachgebietFile(
                source=source_file,
                tags=[
                    Sachgebiet(id="Umwelt", number=1),
                    Sachgebiet(id="Umwelt", number=2),
                ],
            )

    def test_duplicate_numbers_raise(self, source_file: Path) -> None:
        with pytest.raises(ValidationError, match="Duplicate Sachgebiet numbers"):
            SachgebietFile(
                source=source_file,
                tags=[
                    Sachgebiet(id="Umwelt", number=1),
                    Sachgebiet(id="Bildung", number=1),
                ],
            )

    def test_empty_tags_list_is_allowed(self, source_file: Path) -> None:
        assert SachgebietFile(source=source_file, tags=[]).tags == []


# =====================================================================
# SachgebietFile.from_path
# =====================================================================


class TestSachgebietFileFromPath:
    def test_loads_valid_yaml(self, sachgebiet_yaml_file: Path) -> None:
        sf = SachgebietFile.from_path(sachgebiet_yaml_file)
        assert {t.id for t in sf.tags} == {"Umwelt", "Bildung"}

    def test_numbers_are_parsed(self, sachgebiet_yaml_file: Path) -> None:
        sf = SachgebietFile.from_path(sachgebiet_yaml_file)
        numbers = {t.id: t.number for t in sf.tags}
        assert numbers["Umwelt"] == 100
        assert numbers["Bildung"] == 200

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            SachgebietFile.from_path(tmp_path / "nonexistent.yaml")

    def test_duplicate_numbers_in_yaml_raise_value_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "dup.yaml"
        bad.write_text(
            "tags:\n"
            "  - id: Umwelt\n    number: 100\n"
            "  - id: Bildung\n    number: 100\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Validation failed"):
            SachgebietFile.from_path(bad)


# =====================================================================
# SchlagwortIDResolution
# =====================================================================


class TestSchlagwortIDResolution:
    def test_matched_true_when_score_above_zero(self) -> None:
        r = SchlagwortIDResolution(
            original_id="Umwelt", resolved_id="Umwelt", score=0.9
        )
        assert r.matched is True

    def test_matched_false_when_score_is_zero(self) -> None:
        r = SchlagwortIDResolution(
            original_id="Umwelt", resolved_id="Umwelt", score=0.0
        )
        assert r.matched is False

    def test_changed_true_when_ids_differ(self) -> None:
        r = SchlagwortIDResolution(
            original_id="umwelt", resolved_id="Umwelt", score=0.9
        )
        assert r.changed is True

    def test_changed_false_when_ids_are_equal(self) -> None:
        r = SchlagwortIDResolution(
            original_id="Umwelt", resolved_id="Umwelt", score=0.9
        )
        assert r.changed is False

    def test_no_match_score_zero_and_changed_false(self) -> None:
        r = SchlagwortIDResolution(original_id="Xyz", resolved_id="Xyz", score=0.0)
        assert r.matched is False
        assert r.changed is False
