"""Tests for collector_core.normalization.schlagworte."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

import collector_core.normalization.schlagworte as schlagworte_mod
from collector_core.normalization.schlagworte import (
    SchlagwortResolver,
    _build_json,
    _build_json_sachgebiete_no_numbers,
    _canonicalise_id,
    _make_validated_list,
)
from collector_core.schlagworte_model import Sachgebiet, Tag


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture()
def tags_yaml(tmp_path: Path) -> Path:
    """A minimal global-tags YAML with two entries."""
    f = tmp_path / "global_tags.yaml"
    f.write_text(
        "tags:\n"
        "  - id: Digitalisierung\n"
        "    description: Digitale Infrastruktur\n"
        "  - id: Wohnungsbau\n"
        "    description: Sozialer Wohnungsbau\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def sachgebiete_yaml(tmp_path: Path) -> Path:
    """A minimal sachgebiete YAML with two entries."""
    f = tmp_path / "sachgebiete.yaml"
    f.write_text(
        "tags:\n"
        "  - id: Umwelt\n"
        "    number: 100\n"
        "    description: Umweltschutz\n"
        "  - id: Bildung\n"
        "    number: 200\n"
        "    description: Bildungswesen\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def local_tags_yaml(tmp_path: Path) -> Path:
    """A minimal local-tags YAML with one entry."""
    f = tmp_path / "local_tags.yaml"
    f.write_text(
        "tags:\n"
        "  - id: Lokales Thema\n"
        "    description: Nur in diesem Scraper relevant\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def patched_resolver(
    monkeypatch: pytest.MonkeyPatch,
    tags_yaml: Path,
    sachgebiete_yaml: Path,
) -> SchlagwortResolver:
    """A SchlagwortResolver backed by minimal fixture files instead of real mappings."""
    monkeypatch.setattr(schlagworte_mod, "GLOBAL_TAGS_FILES", [tags_yaml])
    monkeypatch.setattr(schlagworte_mod, "SACHGEBIETE_FILES", [sachgebiete_yaml])
    return SchlagwortResolver()


# =====================================================================
# _canonicalise_id
# =====================================================================


class TestCanonicaliseId:
    def test_exact_match_preserved(self) -> None:
        assert _canonicalise_id("Umwelt", {"Umwelt", "Bildung"}) == "Umwelt"

    def test_case_insensitive_match_returns_canonical(self) -> None:
        assert _canonicalise_id("umwelt", {"Umwelt", "Bildung"}) == "Umwelt"

    def test_mixed_case_match(self) -> None:
        assert _canonicalise_id("UMWELT", {"Umwelt"}) == "Umwelt"

    def test_no_match_returns_input_unchanged(self) -> None:
        assert _canonicalise_id("Unbekannt", {"Umwelt", "Bildung"}) == "Unbekannt"

    def test_empty_canonical_set_returns_input(self) -> None:
        assert _canonicalise_id("Umwelt", set()) == "Umwelt"


# =====================================================================
# _build_json
# =====================================================================


class TestBuildJson:
    def test_serialises_tags_to_json_array(self) -> None:
        tags = [Tag(id="Umwelt", description="Natur")]
        result = json.loads(_build_json(tags))
        assert result == [{"id": "Umwelt", "description": "Natur"}]

    def test_empty_list_returns_empty_array(self) -> None:
        assert json.loads(_build_json([])) == []

    def test_preserves_non_ascii_characters(self) -> None:
        tags = [Tag(id="Öffentlichkeit")]
        raw = _build_json(tags)
        assert "Öffentlichkeit" in raw

    def test_multiple_items_preserves_order(self) -> None:
        tags = [Tag(id="Alfa"), Tag(id="Beta"), Tag(id="Gamma")]
        result = json.loads(_build_json(tags))
        assert [r["id"] for r in result] == ["Alfa", "Beta", "Gamma"]


class TestBuildJsonSachgebieteNoNumbers:
    def test_number_field_is_absent(self) -> None:
        sachgebiete = [Sachgebiet(id="Umwelt", number=100, description="Natur")]
        result = json.loads(_build_json_sachgebiete_no_numbers(sachgebiete))
        assert "number" not in result[0]

    def test_id_and_description_are_present(self) -> None:
        sachgebiete = [Sachgebiet(id="Umwelt", number=100, description="Natur")]
        result = json.loads(_build_json_sachgebiete_no_numbers(sachgebiete))
        assert result[0]["id"] == "Umwelt"
        assert result[0]["description"] == "Natur"


# =====================================================================
# _make_validated_list
# =====================================================================


class TestMakeValidatedList:
    @pytest.fixture()
    def str_list_type(self) -> type:
        return _make_validated_list({"Alfa", "Beta", "Gamma"}, "Invalid items")

    @pytest.fixture()
    def int_list_type(self) -> type:
        return _make_validated_list({1, 2, 3}, "Invalid numbers")

    def test_valid_string_values_pass(self, str_list_type: type) -> None:
        adapter = TypeAdapter(str_list_type)
        assert adapter.validate_python(["Alfa", "Beta"]) == ["Alfa", "Beta"]

    def test_invalid_string_raises_validation_error(self, str_list_type: type) -> None:
        adapter = TypeAdapter(str_list_type)
        with pytest.raises(ValidationError, match="Invalid items"):
            adapter.validate_python(["Alfa", "Unknown"])

    def test_empty_list_passes(self, str_list_type: type) -> None:
        adapter = TypeAdapter(str_list_type)
        assert adapter.validate_python([]) == []

    def test_valid_int_values_pass(self, int_list_type: type) -> None:
        adapter = TypeAdapter(int_list_type)
        assert adapter.validate_python([1, 2]) == [1, 2]

    def test_invalid_int_raises_validation_error(self, int_list_type: type) -> None:
        adapter = TypeAdapter(int_list_type)
        with pytest.raises(ValidationError, match="Invalid numbers"):
            adapter.validate_python([1, 99])

    def test_all_invalid_raises(self, str_list_type: type) -> None:
        adapter = TypeAdapter(str_list_type)
        with pytest.raises(ValidationError):
            adapter.validate_python(["X", "Y"])


# =====================================================================
# SchlagwortResolver — construction
# =====================================================================


class TestSchlagwortResolverConstruction:
    def test_constructs_with_real_files(self) -> None:
        resolver = SchlagwortResolver()
        assert resolver._tags
        assert resolver._sachgebiete

    def test_constructs_with_fixture_files(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert len(patched_resolver._sachgebiete) == 2

    def test_sachgebiete_included_in_tags(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        tag_ids = {t.id for t in patched_resolver._tags}
        assert "Umwelt" in tag_ids
        assert "Bildung" in tag_ids

    def test_global_tags_included_in_tags(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        tag_ids = {t.id for t in patched_resolver._tags}
        assert "Digitalisierung" in tag_ids
        assert "Wohnungsbau" in tag_ids


# =====================================================================
# SchlagwortResolver — JSON output
# =====================================================================


class TestGetTagsJson:
    def test_returns_valid_json(self, patched_resolver: SchlagwortResolver) -> None:
        result = json.loads(patched_resolver.get_tags_json())
        assert isinstance(result, list)

    def test_contains_global_tags(self, patched_resolver: SchlagwortResolver) -> None:
        ids = {e["id"] for e in json.loads(patched_resolver.get_tags_json())}
        assert "Digitalisierung" in ids

    def test_contains_sachgebiete(self, patched_resolver: SchlagwortResolver) -> None:
        ids = {e["id"] for e in json.loads(patched_resolver.get_tags_json())}
        assert "Umwelt" in ids

    def test_no_number_field_in_output(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        for entry in json.loads(patched_resolver.get_tags_json()):
            assert "number" not in entry


class TestGetSachgebieteJson:
    def test_returns_valid_json(self, patched_resolver: SchlagwortResolver) -> None:
        result = json.loads(patched_resolver.get_sachgebiete_json())
        assert isinstance(result, list)

    def test_contains_number_field(self, patched_resolver: SchlagwortResolver) -> None:
        result = json.loads(patched_resolver.get_sachgebiete_json())
        assert all("number" in entry for entry in result)

    def test_correct_number_for_id(self, patched_resolver: SchlagwortResolver) -> None:
        result = {
            e["id"]: e["number"]
            for e in json.loads(patched_resolver.get_sachgebiete_json())
        }
        assert result["Umwelt"] == 100
        assert result["Bildung"] == 200


class TestGetSachgebieteNoNumbersJson:
    def test_returns_valid_json(self, patched_resolver: SchlagwortResolver) -> None:
        result = json.loads(patched_resolver.get_sachgebiete_no_numbers_json())
        assert isinstance(result, list)

    def test_number_field_absent(self, patched_resolver: SchlagwortResolver) -> None:
        for entry in json.loads(patched_resolver.get_sachgebiete_no_numbers_json()):
            assert "number" not in entry

    def test_id_and_description_present(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        result = json.loads(patched_resolver.get_sachgebiete_no_numbers_json())
        assert all("id" in e and "description" in e for e in result)


# =====================================================================
# SchlagwortResolver — tag lookups
# =====================================================================


class TestCheckTag:
    def test_known_tag_returns_true(self, patched_resolver: SchlagwortResolver) -> None:
        assert patched_resolver.check_tag("Digitalisierung") is True

    def test_sachgebiet_as_tag_returns_true(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.check_tag("Umwelt") is True

    def test_unknown_tag_returns_false(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.check_tag("NichtVorhanden") is False

    def test_case_sensitive(self, patched_resolver: SchlagwortResolver) -> None:
        assert patched_resolver.check_tag("digitalisierung") is False


# =====================================================================
# SchlagwortResolver — Sachgebiet lookups
# =====================================================================


class TestGetSachgebietNumber:
    def test_known_id_returns_number(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.get_sachgebiet_number("Umwelt") == 100

    def test_unknown_id_raises_key_error(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        with pytest.raises(KeyError, match="NichtVorhanden"):
            patched_resolver.get_sachgebiet_number("NichtVorhanden")


class TestGetSachgebietId:
    def test_known_number_returns_id(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.get_sachgebiet_id(100) == "Umwelt"

    def test_unknown_number_raises_key_error(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        with pytest.raises(KeyError, match="999"):
            patched_resolver.get_sachgebiet_id(999)


class TestCheckSachgebietId:
    def test_known_id_returns_true(self, patched_resolver: SchlagwortResolver) -> None:
        assert patched_resolver.check_sachgebiet_id("Umwelt") is True

    def test_unknown_id_returns_false(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.check_sachgebiet_id("NichtVorhanden") is False


class TestCheckSachgebietNummer:
    def test_known_number_returns_true(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.check_sachgebiet_nummer(100) is True

    def test_unknown_number_returns_false(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        assert patched_resolver.check_sachgebiet_nummer(999) is False


# =====================================================================
# SchlagwortResolver — annotated types
# =====================================================================


class TestSachgebietList:
    def test_valid_ids_pass(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.SachgebietList)
        assert adapter.validate_python(["Umwelt", "Bildung"]) == ["Umwelt", "Bildung"]

    def test_invalid_id_raises(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.SachgebietList)
        with pytest.raises(ValidationError, match="Invalid Sachgebiete"):
            adapter.validate_python(["Umwelt", "NichtVorhanden"])

    def test_empty_list_passes(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.SachgebietList)
        assert adapter.validate_python([]) == []


class TestSachgebieteNumberList:
    def test_valid_numbers_pass(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.SachgebieteNumberList)
        assert adapter.validate_python([100, 200]) == [100, 200]

    def test_invalid_number_raises(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.SachgebieteNumberList)
        with pytest.raises(ValidationError, match="Invalid Sachgebiet-Nummern"):
            adapter.validate_python([100, 999])

    def test_empty_list_passes(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.SachgebieteNumberList)
        assert adapter.validate_python([]) == []


class TestTagList:
    def test_valid_tag_passes(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.TagList)
        assert adapter.validate_python(["Digitalisierung"]) == ["Digitalisierung"]

    def test_sachgebiet_as_tag_passes(
        self, patched_resolver: SchlagwortResolver
    ) -> None:
        adapter = TypeAdapter(patched_resolver.TagList)
        assert adapter.validate_python(["Umwelt"]) == ["Umwelt"]

    def test_invalid_tag_raises(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.TagList)
        with pytest.raises(ValidationError, match="Invalid Tags"):
            adapter.validate_python(["NichtVorhanden"])

    def test_empty_list_passes(self, patched_resolver: SchlagwortResolver) -> None:
        adapter = TypeAdapter(patched_resolver.TagList)
        assert adapter.validate_python([]) == []


# =====================================================================
# SchlagwortResolver — local tags merge behaviour
# =====================================================================


class TestLocalTags:
    def test_local_tag_included(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tags_yaml: Path,
        sachgebiete_yaml: Path,
        local_tags_yaml: Path,
    ) -> None:
        monkeypatch.setattr(schlagworte_mod, "GLOBAL_TAGS_FILES", [tags_yaml])
        monkeypatch.setattr(schlagworte_mod, "SACHGEBIETE_FILES", [sachgebiete_yaml])
        resolver = SchlagwortResolver(local_tags=[local_tags_yaml])
        assert resolver.check_tag("Lokales Thema")

    def test_local_tag_canonicalised_to_global(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        tags_yaml: Path,
        sachgebiete_yaml: Path,
    ) -> None:
        """A local tag whose id matches a global tag case-insensitively is normalised."""
        local = tmp_path / "local.yaml"
        local.write_text(
            "tags:\n  - id: digitalisierung\n    description: lowercase variant\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(schlagworte_mod, "GLOBAL_TAGS_FILES", [tags_yaml])
        monkeypatch.setattr(schlagworte_mod, "SACHGEBIETE_FILES", [sachgebiete_yaml])
        resolver = SchlagwortResolver(local_tags=[local])
        assert resolver.check_tag("Digitalisierung")
        assert not resolver.check_tag("digitalisierung")

    def test_global_overrides_local_description(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        sachgebiete_yaml: Path,
    ) -> None:
        """The global file's description wins over the local file's description."""
        global_yaml = tmp_path / "global.yaml"
        global_yaml.write_text(
            "tags:\n  - id: Thema\n    description: Global description\n",
            encoding="utf-8",
        )
        local_yaml = tmp_path / "local.yaml"
        local_yaml.write_text(
            "tags:\n  - id: Thema\n    description: Local description\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(schlagworte_mod, "GLOBAL_TAGS_FILES", [global_yaml])
        monkeypatch.setattr(schlagworte_mod, "SACHGEBIETE_FILES", [sachgebiete_yaml])
        resolver = SchlagwortResolver(local_tags=[local_yaml])
        tag = next(t for t in resolver._tags if t.id == "Thema")
        assert tag.description == "Global description"

    def test_sachgebiet_overrides_global_tag(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Sachgebiet wins over a global tag with the same id."""
        global_yaml = tmp_path / "global.yaml"
        global_yaml.write_text(
            "tags:\n  - id: Umwelt\n    description: Global description\n",
            encoding="utf-8",
        )
        sachgebiete = tmp_path / "sachgebiete.yaml"
        sachgebiete.write_text(
            "tags:\n"
            "  - id: Umwelt\n"
            "    number: 100\n"
            "    description: Sachgebiet description\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(schlagworte_mod, "GLOBAL_TAGS_FILES", [global_yaml])
        monkeypatch.setattr(schlagworte_mod, "SACHGEBIETE_FILES", [sachgebiete])
        resolver = SchlagwortResolver()
        tag = next(t for t in resolver._tags if t.id == "Umwelt")
        assert tag.description == "Sachgebiet description"


# =====================================================================
# Duplicate Sachgebiet number detection
# =====================================================================


class TestDuplicateSachgebietNumbers:
    def test_duplicate_number_across_files_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        tags_yaml: Path,
    ) -> None:
        file_a = tmp_path / "a.yaml"
        file_a.write_text(
            "tags:\n  - id: Alfa\n    number: 100\n    description: A\n",
            encoding="utf-8",
        )
        file_b = tmp_path / "b.yaml"
        file_b.write_text(
            "tags:\n  - id: Beta\n    number: 100\n    description: B\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(schlagworte_mod, "GLOBAL_TAGS_FILES", [tags_yaml])
        monkeypatch.setattr(schlagworte_mod, "SACHGEBIETE_FILES", [file_a, file_b])
        with pytest.raises(ValueError, match="Duplicate Parlamentsspiegel number 100"):
            SchlagwortResolver()