"""End-to-end smoke tests for the regenerated OpenAPI client.

These exercise the public type signatures together with httpx via
``MockTransport`` so request-time issues like header coercion are caught here
rather than in production.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import pytest

from pazufa_corelib import format_if_modified_since
from pazufa_corelib.api_client.api.sitzung import kal_date_put
from pazufa_corelib.api_client.api.vorgang import vorgang_get_by_id, vorgang_put
from pazufa_corelib.api_client.client import AuthenticatedClient
from pazufa_corelib.api_client.models.doktyp import Doktyp
from pazufa_corelib.api_client.models.dokument import Dokument
from pazufa_corelib.api_client.models.dokument_hash import DokumentHash
from pazufa_corelib.api_client.models.gremium import Gremium
from pazufa_corelib.api_client.models.hash_strategy import HashStrategy
from pazufa_corelib.api_client.models.mime import Mime
from pazufa_corelib.api_client.models.parlament import Parlament
from pazufa_corelib.api_client.models.ressort import Ressort
from pazufa_corelib.api_client.models.sachgebiet import Sachgebiet
from pazufa_corelib.api_client.models.station import Station
from pazufa_corelib.api_client.models.stationstyp import Stationstyp
from pazufa_corelib.api_client.models.vorgang import Vorgang
from pazufa_corelib.api_client.models.vorgangstyp import Vorgangstyp

SCRAPER_ID = "11111111-2222-3333-4444-555555555555"
VORGANG_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
SHA256_HEX = "e" * 64


@pytest.fixture
def captured() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def client(captured: list[dict[str, Any]]) -> AuthenticatedClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(
            {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "content": request.content,
            }
        )
        if request.method == "GET":
            return httpx.Response(304)
        return httpx.Response(201)

    c = AuthenticatedClient(base_url="http://test", token="dummy")  # noqa: S106  # test fixture, not a real credential
    c.set_httpx_client(
        httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    )
    return c


def _vorgang() -> Vorgang:
    return Vorgang(
        api_id=VORGANG_ID,
        titel="Test",
        wahlperiode=20,
        verfassungsaendernd=False,
        typ=Vorgangstyp.BU_EINSPRUCH_INIBREG,
        initiatoren=[],
        stationen=[],
    )


def test_if_modified_since_helper_round_trips_through_client(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    ims = format_if_modified_since(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    vorgang_get_by_id.sync_detailed(
        api_id=VORGANG_ID,
        client=client,
        if_modified_since=ims,
    )
    # Spec 0.2.5 had spelled this header "if_modified_since"; underscores make
    # it a genuinely different header on the wire, not a case variant. 0.2.7
    # restores the standard "If-Modified-Since" spelling, so the value is pinned
    # here to make a further change visible.
    assert captured[-1]["headers"]["if-modified-since"] == "2024-01-01T00:00:00+00:00"


def test_scraper_id_header_is_sent_on_vorgang_put(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    vorgang_put.sync_detailed(client=client, body=_vorgang(), x_scraper_id=SCRAPER_ID)
    assert captured[-1]["headers"]["x-scraper-id"] == SCRAPER_ID


def test_scraper_id_header_is_sent_on_kal_date_put(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    """Spec 0.2.7 restored ``X-Scraper-Id`` on the calendar collector endpoint.

    0.2.5 had dropped it while ``PUT /api/v2/vorgang`` kept it, which looked
    accidental; 0.2.7 confirms it was. The header is required again, so
    ``kal_date_put`` takes ``x_scraper_id`` as a mandatory argument.
    """
    kal_date_put.sync_detailed(
        Parlament.BT,
        datetime(2024, 1, 1, tzinfo=timezone.utc).date(),
        client=client,
        body=[],
        x_scraper_id=SCRAPER_ID,
    )
    assert captured[-1]["headers"]["x-scraper-id"] == SCRAPER_ID


# --- Spec 0.2.5 model surface -------------------------------------------------


def _dokument(**overrides: Any) -> Dokument:
    kwargs: dict[str, Any] = {
        "titel": "Testdokument",
        "link": "https://example.com/doc.pdf",
        "hash_": SHA256_HEX,
        "typ": Doktyp.ENTWURF,
        "volltext": "Volltext",
        "autoren": [],
        "zp_modifiziert": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "zp_referenz": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    kwargs.update(overrides)
    return Dokument(**kwargs)


def test_dokument_hash_accepts_a_plain_hex_string() -> None:
    """0.2.5 retyped ``hash`` as ``oneOf[string, DokumentHash[]]``.

    The scalar arm is what every existing collector sends, so it has to keep
    surviving a serialise/parse round trip unchanged.
    """
    payload = _dokument().to_dict()
    assert payload["hash"] == SHA256_HEX
    assert Dokument.from_dict(payload).hash_ == SHA256_HEX


def test_dokument_hash_accepts_a_list_of_structured_hashes() -> None:
    dok = _dokument(
        hash_=[
            DokumentHash(
                value=SHA256_HEX,
                strategy=HashStrategy.SHA256BYTES,
                mime=Mime.APPLICATIONPDF,
            )
        ]
    )
    payload = dok.to_dict()
    assert payload["hash"] == [
        {
            "value": SHA256_HEX,
            "strategy": "sha256+bytes",
            "mime": "application/pdf",
        }
    ]

    parsed = Dokument.from_dict(payload)
    assert isinstance(parsed.hash_, list)
    assert parsed.hash_[0].strategy == HashStrategy.SHA256BYTES
    assert parsed.hash_[0].mime == Mime.APPLICATIONPDF


def test_dokument_carries_subdoc_id() -> None:
    """New in 0.2.5: distinguishes sections that legitimately share a hash."""
    payload = _dokument(subdoc_id=3).to_dict()
    assert payload["subdoc_id"] == 3
    assert Dokument.from_dict(payload).subdoc_id == 3


def test_vorgang_carries_ressort_and_sachgebiete() -> None:
    vorgang = _vorgang()
    vorgang.ressort = Ressort.INNERES
    vorgang.sachgebiete = [Sachgebiet.VALUE_1010, Sachgebiet.VALUE_2000]

    payload = vorgang.to_dict()
    assert payload["ressort"] == "Inneres"
    assert payload["sachgebiete"] == [1010, 2000]

    parsed = Vorgang.from_dict(payload)
    assert parsed.ressort == Ressort.INNERES
    assert parsed.sachgebiete == [Sachgebiet.VALUE_1010, Sachgebiet.VALUE_2000]


@pytest.mark.parametrize("value", ["eckpunktepapier", "gesetz"])
def test_doktyp_gained_0_2_5_values(value: str) -> None:
    assert Doktyp(value).value == value


@pytest.mark.parametrize(
    "value",
    ["parl-antragsst", "parl-vermittas", "preparl-formvs"],
)
def test_stationstyp_gained_0_2_5_values(value: str) -> None:
    assert Stationstyp(value).value == value


def test_stationstyp_verfgstop_was_renamed_in_0_2_7() -> None:
    """``parl-verfgstop`` (new in 0.2.5) became ``postparl-vgstp`` in 0.2.7.

    A rename, not an addition: the old wire value is gone, so collectors that
    emitted it must be updated. Pinned in both directions so a revert upstream
    is noticed.
    """
    assert Stationstyp("postparl-vgstp") is Stationstyp.POSTPARL_VGSTP
    with pytest.raises(ValueError, match="parl-verfgstop"):
        Stationstyp("parl-verfgstop")


def test_station_no_longer_accepts_trojanergefahr() -> None:
    """0.2.5 removed ``Station.trojanergefahr`` outright.

    Collectors that scored documents for it (the BW scraper does) have nowhere
    to put the value now. Pinned so a reinstatement upstream is noticed.
    """
    with pytest.raises(TypeError):
        Station(  # type: ignore[call-arg]
            typ=Stationstyp.PARL_INITIATIV,
            dokumente=[],
            zp_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            gremium=Gremium(name="Plenum", parlament=Parlament.BW, wahlperiode=17),
            trojanergefahr=2,
        )


def test_vorgang_put_serialises_the_full_0_2_5_surface_over_the_wire(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    """The new fields must survive the actual httpx request, not just to_dict."""
    vorgang = _vorgang()
    vorgang.ressort = Ressort.INNERES
    vorgang.sachgebiete = [Sachgebiet.VALUE_1010]
    vorgang.stationen = [
        Station(
            typ=Stationstyp.PREPARL_FORMVS,
            dokumente=[_dokument(subdoc_id=1, typ=Doktyp.ECKPUNKTEPAPIER)],
            zp_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            gremium=Gremium(name="Plenum", parlament=Parlament.BW, wahlperiode=17),
        )
    ]

    vorgang_put.sync_detailed(client=client, body=vorgang, x_scraper_id=SCRAPER_ID)

    body = json.loads(captured[-1]["content"])
    assert body["ressort"] == "Inneres"
    assert body["sachgebiete"] == [1010]
    station = body["stationen"][0]
    assert station["typ"] == "preparl-formvs"
    assert station["dokumente"][0]["typ"] == "eckpunktepapier"
    assert station["dokumente"][0]["subdoc_id"] == 1
    assert station["dokumente"][0]["hash"] == SHA256_HEX
