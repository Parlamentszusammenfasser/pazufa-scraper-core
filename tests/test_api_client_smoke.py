"""End-to-end smoke tests for the regenerated OpenAPI client.

These exercise the public type signatures together with httpx via
``MockTransport`` so request-time issues like header coercion are caught here
rather than in production.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import pytest

from corelib import format_if_modified_since
from corelib.api_client.api.sitzung import kal_date_put
from corelib.api_client.api.vorgang import vorgang_get_by_id, vorgang_put
from corelib.api_client.client import AuthenticatedClient
from corelib.api_client.models.parlament import Parlament
from corelib.api_client.models.vorgang import Vorgang
from corelib.api_client.models.vorgangstyp import Vorgangstyp

SCRAPER_ID = "11111111-2222-3333-4444-555555555555"
VORGANG_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


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
            }
        )
        if request.method == "GET":
            return httpx.Response(304)
        return httpx.Response(201)

    c = AuthenticatedClient(base_url="http://test", token="dummy")
    c._client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://test"
    )
    return c


def _vorgang() -> Vorgang:
    return Vorgang(
        api_id=VORGANG_ID,
        titel="Test",
        wahlperiode=20,
        verfassungsaendernd=False,
        typ=Vorgangstyp.GG_EINSPRUCH,
        initiatoren=[],
        stationen=[],
    )


def test_if_modified_since_helper_round_trips_through_client(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    ims = format_if_modified_since(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    vorgang_get_by_id.sync_detailed(
        vorgang_id=VORGANG_ID,
        client=client,
        if_modified_since=ims,
    )
    assert captured[-1]["headers"]["if-modified-since"] == "2024-01-01T00:00:00+00:00"


def test_scraper_id_header_is_sent_on_vorgang_put(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    vorgang_put.sync_detailed(client=client, body=_vorgang(), x_scraper_id=SCRAPER_ID)
    assert captured[-1]["headers"]["x-scraper-id"] == SCRAPER_ID


def test_scraper_id_header_is_sent_on_kal_date_put(
    client: AuthenticatedClient, captured: list[dict[str, Any]]
) -> None:
    kal_date_put.sync_detailed(
        Parlament.BT,
        datetime(2024, 1, 1).date(),
        client=client,
        body=[],
        x_scraper_id=SCRAPER_ID,
    )
    assert captured[-1]["headers"]["x-scraper-id"] == SCRAPER_ID
