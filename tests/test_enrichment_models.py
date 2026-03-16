"""Tests for enrichment Pydantic models."""

import pytest
from pydantic import ValidationError

from collector_core.llm.models import (
    KurztitelResult,
    MeinungResult,
    SchlagworteResult,
    VerfassungsaenderndResult,
    ZusammenfassungResult,
)


class TestKurztitelResult:
    def test_valid(self) -> None:
        r = KurztitelResult(kurztitel="Stärkung der Kinderrechte")
        assert r.kurztitel == "Stärkung der Kinderrechte"

    def test_empty_kurztitel_raises(self) -> None:
        with pytest.raises(ValidationError):
            KurztitelResult(kurztitel="")

    def test_serialization(self) -> None:
        r = KurztitelResult(kurztitel="Test")
        d = r.model_dump()
        assert d == {"kurztitel": "Test"}


class TestZusammenfassungResult:
    def test_valid(self) -> None:
        r = ZusammenfassungResult(zusammenfassung="Eine Zusammenfassung.")
        assert r.zusammenfassung == "Eine Zusammenfassung."

    def test_empty_zusammenfassung_raises(self) -> None:
        with pytest.raises(ValidationError):
            ZusammenfassungResult(zusammenfassung="")

    def test_serialization(self) -> None:
        r = ZusammenfassungResult(zusammenfassung="Text")
        assert r.model_dump() == {"zusammenfassung": "Text"}


class TestSchlagworteResult:
    def test_valid_sachgebiete(self) -> None:
        r = SchlagworteResult(
            sachgebiete=["Bildung", "Schulen"],
            schlagworte=["lehrermangel"],
        )
        assert r.sachgebiete == ["Bildung", "Schulen"]
        assert r.schlagworte == ["lehrermangel"]

    def test_invalid_sachgebiete_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid Sachgebiete"):
            SchlagworteResult(
                sachgebiete=["Bildung", "Erfundenes Sachgebiet"],
                schlagworte=["test"],
            )

    def test_empty_sachgebiete_valid(self) -> None:
        r = SchlagworteResult(sachgebiete=[], schlagworte=[])
        assert r.sachgebiete == []

    def test_all_valid_sachgebiete_pass(self) -> None:
        """A few known taxonomy entries should validate fine."""
        r = SchlagworteResult(
            sachgebiete=[
                "Staat und Politik",
                "Energie",
                "Datenschutz",
                "Glücksspiel",
            ],
            schlagworte=["test"],
        )
        assert len(r.sachgebiete) == 4

    def test_duplicate_sachgebiete_deduped(self) -> None:
        r = SchlagworteResult(
            sachgebiete=["Bildung", "Schulen", "Bildung"],
            schlagworte=["test"],
        )
        assert r.sachgebiete == ["Bildung", "Schulen"]

    def test_serialization(self) -> None:
        r = SchlagworteResult(sachgebiete=["Bildung"], schlagworte=["test"])
        d = r.model_dump()
        assert d == {"sachgebiete": ["Bildung"], "schlagworte": ["test"]}


class TestMeinungResult:
    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_valid_scores(self, score: int) -> None:
        r = MeinungResult(meinung=score, begruendung="Begründung.")
        assert r.meinung == score

    @pytest.mark.parametrize("score", [0, 6, -1, 10])
    def test_invalid_scores(self, score: int) -> None:
        with pytest.raises(ValidationError):
            MeinungResult(meinung=score, begruendung="Begründung.")

    def test_empty_begruendung_raises(self) -> None:
        with pytest.raises(ValidationError):
            MeinungResult(meinung=3, begruendung="")

    def test_serialization(self) -> None:
        r = MeinungResult(meinung=3, begruendung="Neutral.")
        d = r.model_dump()
        assert d == {"meinung": 3, "begruendung": "Neutral."}


class TestVerfassungsaenderndResult:
    def test_true(self) -> None:
        r = VerfassungsaenderndResult(
            ist_verfassungsaendernd=True,
            begruendung="Ändert Artikel 22.",
        )
        assert r.ist_verfassungsaendernd is True

    def test_false(self) -> None:
        r = VerfassungsaenderndResult(
            ist_verfassungsaendernd=False,
            begruendung="Kein Verfassungsbezug.",
        )
        assert r.ist_verfassungsaendernd is False

    def test_empty_begruendung_raises(self) -> None:
        with pytest.raises(ValidationError):
            VerfassungsaenderndResult(ist_verfassungsaendernd=True, begruendung="")

    def test_serialization(self) -> None:
        r = VerfassungsaenderndResult(
            ist_verfassungsaendernd=False, begruendung="Test."
        )
        d = r.model_dump()
        assert d == {"ist_verfassungsaendernd": False, "begruendung": "Test."}
