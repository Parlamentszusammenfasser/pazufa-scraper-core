"""Tests for enrichment prompt templates."""

from collector_core.enrichment.prompts import (
    KURZTITEL_PROMPT,
    MEINUNG_PROMPT,
    SCHLAGWORTE_PROMPT,
    VERFASSUNGSAENDERND_PROMPT,
    ZUSAMMENFASSUNG_PROMPT,
    format_sachgebiete_list,
)
from collector_core.enrichment.sachgebiete_taxonomy import SACHGEBIETE_NAMES


class TestPromptFormatting:
    def test_kurztitel_prompt(self) -> None:
        result = KURZTITEL_PROMPT.format(titel="Gesetzentwurf", abstract="Ein Abstract.")
        assert "Gesetzentwurf" in result
        assert "Ein Abstract." in result

    def test_zusammenfassung_prompt(self) -> None:
        result = ZUSAMMENFASSUNG_PROMPT.format(titel="Titel", text="Gesetzestext hier.")
        assert "Titel" in result
        assert "Gesetzestext hier." in result

    def test_schlagworte_prompt(self) -> None:
        result = SCHLAGWORTE_PROMPT.format(
            sachgebiete_list="- Bildung\n- Schulen",
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


class TestFormatSachgebieteListe:
    def test_returns_bulleted_list(self) -> None:
        result = format_sachgebiete_list()
        lines = result.strip().split("\n")
        assert len(lines) == len(SACHGEBIETE_NAMES)
        assert all(line.startswith("- ") for line in lines)

    def test_contains_known_entries(self) -> None:
        result = format_sachgebiete_list()
        assert "- Bildung" in result
        assert "- Datenschutz" in result
        assert "- Glücksspiel" in result

    def test_excludes_special_entries(self) -> None:
        result = format_sachgebiete_list()
        assert "Unbekannt" not in result
        assert "ohne@-Systematik" not in result
