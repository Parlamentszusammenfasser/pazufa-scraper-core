"""Tests for enrichment Pydantic models."""

import pytest
from pydantic import ValidationError

from pazufa_corelib.llm.models import (
    ExpertenResult,
    ExpertenResultNoLobbyregister,
    ExtractedExpert,
    ExtractedExpertNoLobbyregister,
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
    # A realistic, non-degenerate summary used across the happy-path tests.
    VALID = (
        "Das Gesetz stärkt die Rechte der Bezirke und ordnet ihre Finanzierung "
        "neu. Es regelt, welche Aufgaben künftig auf Bezirksebene erledigt werden."
    )

    def test_valid(self) -> None:
        r = ZusammenfassungResult(zusammenfassung=self.VALID)
        assert r.zusammenfassung == self.VALID

    def test_empty_zusammenfassung_raises(self) -> None:
        with pytest.raises(ValidationError):
            ZusammenfassungResult(zusammenfassung="")

    def test_too_short_raises(self) -> None:
        """Truncated/degenerate output below the minimum length is rejected."""
        with pytest.raises(ValidationError):
            ZusammenfassungResult(zusammenfassung="Zu kurz.")

    @pytest.mark.parametrize(
        "leaked",
        [
            # Imperative task framing.
            "Bitte erstelle eine Zusammenfassung des vorliegenden Dokuments zum "
            "Gesetz zur Stärkung der Bezirke (BeStG).",
            "Erstelle einen kompakten Fließtext zu diesem parlamentarischen Vorgang "
            "in allgemeinverständlicher Sprache.",
            # Analyst persona leaked from the prompt.
            "Du bist ein parlamentarischer Analyst und fasst das folgende Dokument "
            "sachlich und verständlich zusammen.",
            # Summarization instruction echoed verbatim.
            "Fasse das folgende parlamentarische Dokument in sachlicher und gut "
            "verständlicher Sprache zusammen.",
            # Historically observed length hint, dash form.
            "Eine 150-250 Wörter lange Zusammenfassung des Dokuments in deutscher "
            "Sprache zum Thema Bezirksstärkung.",
            # Same hint in "bis" form (defensive: no longer in the prompt).
            "Strebe einen Umfang von etwa 150 bis 250 Wörtern an und vermeide "
            "juristische Fachsprache, wo möglich.",
        ],
    )
    def test_prompt_echo_rejected(self, leaked: str) -> None:
        """Output that parrots the prompt/schema is rejected (issue #104)."""
        with pytest.raises(ValidationError):
            ZusammenfassungResult(zusammenfassung=leaked)

    def test_legitimate_summary_not_falsely_rejected(self) -> None:
        """A normal summary mentioning numbers must not trip the echo guard."""
        text = (
            "Der Entwurf sieht vor, dass rund 250 zusätzliche Stellen geschaffen "
            "werden. Die Kosten trägt das Land, das Gesetz tritt 2027 in Kraft."
        )
        r = ZusammenfassungResult(zusammenfassung=text)
        assert r.zusammenfassung == text

    def test_serialization(self) -> None:
        r = ZusammenfassungResult(zusammenfassung=self.VALID)
        assert r.model_dump() == {"zusammenfassung": self.VALID}


class TestSchlagworteResult:
    """Tests for SchlagworteResult with SchlagwortResolver-based validation."""

    def _ctx(self) -> dict[str, object]:
        """Build a validation context with a SchlagwortResolver."""
        from pazufa_corelib.normalization.schlagworte import SchlagwortResolver

        return {"resolver": SchlagwortResolver()}

    def test_valid_sachgebiete_with_resolver(self) -> None:
        r = SchlagworteResult.model_validate(
            {"sachgebiete": ["Bildung", "Schulen"], "schlagworte": ["lehrermangel"]},
            context=self._ctx(),
        )
        assert r.sachgebiete == ["Bildung", "Schulen"]
        assert r.schlagworte == ["lehrermangel"]

    def test_invalid_sachgebiete_dropped_with_resolver(self) -> None:
        """Invalid entries are silently dropped (strict fuzzy matching)."""
        r = SchlagworteResult.model_validate(
            {
                "sachgebiete": ["Bildung", "Komplett Erfundenes Ding"],
                "schlagworte": ["test"],
            },
            context=self._ctx(),
        )
        assert r.sachgebiete == ["Bildung"]

    def test_fuzzy_match_corrects_typo(self) -> None:
        """A close typo like 'Bildun' should be resolved to 'Bildung'."""
        r = SchlagworteResult.model_validate(
            {"sachgebiete": ["Bildun"], "schlagworte": ["test"]},
            context=self._ctx(),
        )
        assert "Bildung" in r.sachgebiete

    def test_empty_sachgebiete_valid(self) -> None:
        r = SchlagworteResult.model_validate(
            {"sachgebiete": [], "schlagworte": []},
            context=self._ctx(),
        )
        assert r.sachgebiete == []

    def test_all_valid_sachgebiete_pass(self) -> None:
        """A few known taxonomy entries should validate fine."""
        r = SchlagworteResult.model_validate(
            {
                "sachgebiete": [
                    "Staat und Politik",
                    "Energie",
                    "Datenschutz",
                    "Glücksspiel",
                ],
                "schlagworte": ["test"],
            },
            context=self._ctx(),
        )
        assert len(r.sachgebiete) == 4

    def test_duplicate_sachgebiete_deduped(self) -> None:
        r = SchlagworteResult.model_validate(
            {
                "sachgebiete": ["Bildung", "Schulen", "Bildung"],
                "schlagworte": ["test"],
            },
            context=self._ctx(),
        )
        assert r.sachgebiete == ["Bildung", "Schulen"]

    def test_without_resolver_only_deduplicates(self) -> None:
        """Without a resolver in context, validation only deduplicates."""
        r = SchlagworteResult(
            sachgebiete=["Bildung", "Anything", "Bildung"],
            schlagworte=["test"],
        )
        assert r.sachgebiete == ["Bildung", "Anything"]

    def test_serialization(self) -> None:
        r = SchlagworteResult.model_validate(
            {"sachgebiete": ["Bildung"], "schlagworte": ["test"]},
            context=self._ctx(),
        )
        d = r.model_dump()
        assert d == {"sachgebiete": ["Bildung"], "schlagworte": ["test"]}


class TestMeinungResult:
    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_valid_scores(self, score: int) -> None:
        r = MeinungResult(meinung=score, begruendung="Begründung.")  # type: ignore[arg-type]
        assert r.meinung == score

    @pytest.mark.parametrize("score", [0, 6, -1, 10])
    def test_invalid_scores(self, score: int) -> None:
        with pytest.raises(ValidationError):
            MeinungResult(meinung=score, begruendung="Begründung.")  # type: ignore[arg-type]

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


class TestExtractedExpert:
    def test_valid_full(self) -> None:
        e = ExtractedExpert(
            person="Prof. Dr. Susanne Meyer",
            organisation="Universität Heidelberg",
            fachgebiet="Verfassungsrecht",
            lobbyregister="https://www.lobbyregister.bundestag.de/suche/12345",
        )
        assert e.person == "Prof. Dr. Susanne Meyer"
        assert e.organisation == "Universität Heidelberg"
        assert e.fachgebiet == "Verfassungsrecht"
        assert e.lobbyregister == "https://www.lobbyregister.bundestag.de/suche/12345"

    def test_valid_lobbyregister_as_id(self) -> None:
        e = ExtractedExpert(organisation="DGB", lobbyregister="R001234")
        assert e.lobbyregister == "R001234"

    def test_person_none(self) -> None:
        e = ExtractedExpert(organisation="Deutscher Gewerkschaftsbund")
        assert e.person is None
        assert e.fachgebiet is None
        assert e.lobbyregister is None

    def test_empty_organisation_raises(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedExpert(organisation="")

    def test_serialization(self) -> None:
        e = ExtractedExpert(person="Max Mustermann", organisation="Privatperson")
        d = e.model_dump()
        assert d["person"] == "Max Mustermann"
        assert d["organisation"] == "Privatperson"
        assert d["fachgebiet"] is None
        assert d["lobbyregister"] is None


class TestExpertenResult:
    def test_valid_single(self) -> None:
        r = ExpertenResult(
            experten=[
                ExtractedExpert(organisation="Bundesverband der Deutschen Industrie")
            ]
        )
        assert len(r.experten) == 1

    def test_valid_multiple(self) -> None:
        r = ExpertenResult(
            experten=[
                ExtractedExpert(
                    person="Dr. Anna Schmidt",
                    organisation="Technische Universität Berlin",
                ),
                ExtractedExpert(organisation="ver.di"),
            ]
        )
        assert len(r.experten) == 2

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValidationError):
            ExpertenResult(experten=[])


class TestExtractedExpertNoLobbyregister:
    def test_valid_full(self) -> None:
        e = ExtractedExpertNoLobbyregister(
            person="Prof. Dr. Susanne Meyer",
            organisation="Universität Heidelberg",
            fachgebiet="Verfassungsrecht",
        )
        assert e.person == "Prof. Dr. Susanne Meyer"
        assert e.organisation == "Universität Heidelberg"
        assert e.fachgebiet == "Verfassungsrecht"

    def test_person_none(self) -> None:
        e = ExtractedExpertNoLobbyregister(organisation="Deutscher Gewerkschaftsbund")
        assert e.person is None
        assert e.fachgebiet is None

    def test_empty_organisation_raises(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedExpertNoLobbyregister(organisation="")

    def test_serialization(self) -> None:
        e = ExtractedExpertNoLobbyregister(
            person="Max Mustermann", organisation="Privatperson"
        )
        d = e.model_dump()
        assert d["person"] == "Max Mustermann"
        assert d["organisation"] == "Privatperson"
        assert d["fachgebiet"] is None
        assert "lobbyregister" not in d

    def test_no_lobbyregister_field(self) -> None:
        """Verify the model has no lobbyregister field to prevent hallucination."""
        e = ExtractedExpertNoLobbyregister(organisation="Test Org")
        assert not hasattr(e, "lobbyregister")


class TestExpertenResultNoLobbyregister:
    def test_valid_single(self) -> None:
        r = ExpertenResultNoLobbyregister(
            experten=[
                ExtractedExpertNoLobbyregister(
                    organisation="Bundesverband der Deutschen Industrie"
                )
            ]
        )
        assert len(r.experten) == 1

    def test_valid_multiple(self) -> None:
        r = ExpertenResultNoLobbyregister(
            experten=[
                ExtractedExpertNoLobbyregister(
                    person="Dr. Anna Schmidt",
                    organisation="Technische Universität Berlin",
                ),
                ExtractedExpertNoLobbyregister(organisation="ver.di"),
            ]
        )
        assert len(r.experten) == 2

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValidationError):
            ExpertenResultNoLobbyregister(experten=[])
