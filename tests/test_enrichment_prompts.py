"""Tests for enrichment prompt templates."""

import json

from pazufa_corelib.llm.prompts import (
    EXPERTEN_PROMPT,
    KURZTITEL_PROMPT,
    MEINUNG_PROMPT,
    SCHLAGWORTE_PROMPT,
    VERFASSUNGSAENDERND_PROMPT,
    ZUSAMMENFASSUNG_GESETZENTWURF_PROMPT,
    ZUSAMMENFASSUNG_PROMPT,
    format_sachgebiete_list,
)
from pazufa_corelib.normalization.schlagworte import SchlagwortResolver


class TestPromptFormatting:
    def test_kurztitel_prompt(self) -> None:
        result = KURZTITEL_PROMPT.format(
            titel="Gesetzentwurf", abstract="Ein Abstract."
        )
        assert "Gesetzentwurf" in result
        assert "Ein Abstract." in result

    def test_zusammenfassung_prompt(self) -> None:
        result = ZUSAMMENFASSUNG_PROMPT.format(titel="Titel", text="Gesetzestext hier.")
        assert "Titel" in result
        assert "Gesetzestext hier." in result
        # Generic prompt should not contain Gesetzentwurf-specific structure.
        assert "Geänderte Vorschriften" not in result
        assert "Inkrafttreten" not in result
        # Public-facing framing for non-expert readers (issue #104).
        assert "Bürgerinnen und Bürger" in result

    def test_zusammenfassung_gesetzentwurf_prompt(self) -> None:
        result = ZUSAMMENFASSUNG_GESETZENTWURF_PROMPT.format(
            titel="Gesetzentwurf", text="Gesetzestext hier."
        )
        assert "Gesetzentwurf" in result
        assert "Gesetzestext hier." in result
        # Gesetzentwurf-specific structure must be present.
        assert "Geänderte Vorschriften" in result
        assert "Inkrafttreten" in result
        # Public-facing framing for non-expert readers (issue #104).
        assert "Bürgerinnen und Bürger" in result

    def test_schlagworte_prompt(self) -> None:
        result = SCHLAGWORTE_PROMPT.format(
            sachgebiete_list='[{"id": "Bildung", "description": "..."}]',
            vorgang_titel="Schulgesetz",
            vorgang_vnr="7/1234",
            dok_typ="Gesetzentwurf",
            titel="Entwurf Schulgesetz",
            text="Text des Gesetzentwurfs.",
        )
        assert "Bildung" in result
        assert "Schulgesetz" in result
        assert "7/1234" in result
        assert "Gesetzentwurf" in result

    def test_meinung_prompt(self) -> None:
        result = MEINUNG_PROMPT.format(
            dok_typ="Stellungnahme",
            titel="Titel",
            text="Bewertungstext.",
        )
        assert "Stellungnahme" in result
        assert "Bewertungstext." in result

    def test_verfassungsaendernd_prompt(self) -> None:
        result = VERFASSUNGSAENDERND_PROMPT.format(
            land="Brandenburg",
            titel="Verfassungsänderung",
            schlagworte="Verfassung, Grundrechte",
            text="Artikel 22 wird geändert.",
        )
        assert "Brandenburg" in result
        assert "Verfassungsänderung" in result
        assert "Verfassung, Grundrechte" in result

    def test_verfassungsaendernd_prompt_other_state(self) -> None:
        result = VERFASSUNGSAENDERND_PROMPT.format(
            land="Bayern",
            titel="Titel",
            schlagworte="",
            text="Text.",
        )
        assert "Bayern" in result
        assert "Brandenburg" not in result

    def test_experten_prompt(self) -> None:
        result = EXPERTEN_PROMPT.format(
            dok_typ="stellungnahme",
            titel="Stellungnahme zum Klimaschutzgesetz",
            text="Eingereicht von Prof. Dr. Anna Müller, Universität Hamburg.",
        )
        assert "stellungnahme" in result
        assert "Stellungnahme zum Klimaschutzgesetz" in result
        assert "Prof. Dr. Anna Müller" in result


class TestFormatSachgebieteListe:
    def test_returns_valid_json(self) -> None:
        resolver = SchlagwortResolver()
        result = format_sachgebiete_list(resolver)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_entries_have_id_and_description(self) -> None:
        resolver = SchlagwortResolver()
        result = format_sachgebiete_list(resolver)
        parsed = json.loads(result)
        for entry in parsed:
            assert "id" in entry
            assert "description" in entry

    def test_contains_known_entries(self) -> None:
        resolver = SchlagwortResolver()
        result = format_sachgebiete_list(resolver)
        assert "Bildung" in result
        assert "Datenschutz" in result
        assert "Glücksspiel" in result

    def test_excludes_sachgebiet_numbers(self) -> None:
        resolver = SchlagwortResolver()
        result = format_sachgebiete_list(resolver)
        parsed = json.loads(result)
        for entry in parsed:
            assert "number" not in entry

    def test_excludes_special_entries(self) -> None:
        resolver = SchlagwortResolver()
        result = format_sachgebiete_list(resolver)
        assert "Unbekannt" not in result
        assert "ohne@-Systematik" not in result
