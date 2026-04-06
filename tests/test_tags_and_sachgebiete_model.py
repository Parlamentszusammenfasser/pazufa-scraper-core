"""Tests for tags and sachgebiete pydantic models."""

import pytest
from pydantic import ValidationError

from collector_core.tags_and_sachgebiete_model import (
    Tag,
    Sachgebiet,
    TagFile,
    SachgebietFile,
)


class TestTagIdValidation:
    def test_valid_id(self) -> None:
        assert Tag(id="Umwelt").id == "Umwelt"

    def test_valid_id_with_hyphen(self) -> None:
        assert Tag(id="Baden-Württemberg").id == "Baden-Württemberg"

    def test_valid_id_with_umlaut(self) -> None:
        assert Tag(id="Öffentlichkeit").id == "Öffentlichkeit"

    def test_valid_id_with_eszett(self) -> None:
        assert Tag(id="Straßenrecht").id == "Straßenrecht"

    def test_id_with_number_raises(self) -> None:
        with pytest.raises(ValidationError):
            Tag(id="Tag1")

    def test_id_with_special_char_raises(self) -> None:
        with pytest.raises(ValidationError):
            Tag(id="Tag!")

    def test_description_defaults_to_none(self) -> None:
        assert Tag(id="Umwelt").description is None

    def test_description_can_be_set(self) -> None:
        assert (
            Tag(id="Umwelt", description="Umweltschutz").description == "Umweltschutz"
        )


class TestSachgebiet:
    def test_valid_sachgebiet(self) -> None:
        s = Sachgebiet(id="Umwelt", number=1)
        assert s.number == 1

    def test_number_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            Sachgebiet(id="Umwelt", number=0)

    def test_number_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            Sachgebiet(id="Umwelt", number=-1)

    def test_inherits_id_validation(self) -> None:
        with pytest.raises(ValidationError):
            Sachgebiet(id="Tag1", number=1)


class TestTagFile:
    def test_valid_tag_file(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "tags.yaml"
        f.touch()
        tf = TagFile(source=f, tags=[Tag(id="Umwelt"), Tag(id="Bildung")])
        assert len(tf.tags) == 2

    def test_duplicate_ids_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "tags.yaml"
        f.touch()
        with pytest.raises(ValidationError, match="Duplicate IDs"):
            TagFile(source=f, tags=[Tag(id="Umwelt"), Tag(id="Umwelt")])

    def test_empty_tags_allowed(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "tags.yaml"
        f.touch()
        tf = TagFile(source=f, tags=[])
        assert tf.tags == []

    def test_nonexistent_source_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        with pytest.raises(ValidationError):
            TagFile(source=tmp_path / "missing.yaml", tags=[])


class TestSachgebietFile:
    def test_valid_sachgebiet_file(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "sachgebiete.yaml"
        f.touch()
        sf = SachgebietFile(
            source=f,
            tags=[
                Sachgebiet(id="Umwelt", number=1),
                Sachgebiet(id="Bildung", number=2),
            ],
        )
        assert len(sf.tags) == 2

    def test_duplicate_ids_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "sachgebiete.yaml"
        f.touch()
        with pytest.raises(ValidationError, match="Duplicate IDs"):
            SachgebietFile(
                source=f,
                tags=[
                    Sachgebiet(id="Umwelt", number=1),
                    Sachgebiet(id="Umwelt", number=2),
                ],
            )

    def test_duplicate_numbers_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "sachgebiete.yaml"
        f.touch()
        with pytest.raises(ValidationError, match="Duplicate Sachgebiet numbers"):
            SachgebietFile(
                source=f,
                tags=[
                    Sachgebiet(id="Umwelt", number=1),
                    Sachgebiet(id="Bildung", number=1),
                ],
            )
