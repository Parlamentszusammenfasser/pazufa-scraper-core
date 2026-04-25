from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.vorgang import Vorgang
from ...types import Response


def _get_kwargs(
    vorgang_id: UUID,
    *,
    body: Vorgang,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v2/vorgang/{vorgang_id}".format(
            vorgang_id=quote(str(vorgang_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | None:
    if response.status_code == 201:
        return None

    if response.status_code == 304:
        return None

    if response.status_code == 403:
        return None

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    vorgang_id: UUID,
    *,
    client: AuthenticatedClient,
    body: Vorgang,
) -> Response[Any]:
    """Administrative endpoint to directly set or replace a legislative process without merging or
    matching. Replaces the entire process data if it exists, or creates a new one if it doesn't.

    Args:
        vorgang_id (UUID):
        body (Vorgang): 'Master-Objekt' der API. Der Wrapper um Stationen, die den
            Beratungsverlauf tatsächlich beschreiben. Ein Vorgang kann dabei nicht nur ein Gesetz,
            sondern auch ein parlamentarischer Antrag sein. Example: {'api_id':
            '123e4567-e89b-12d3-a456-426614174000', 'ids': [{'id': '20/12345', 'typ': 'initdrucks'},
            {'id': 'WR-2024-01', 'typ': 'vorgnr'}], 'initiatoren': [{'fachgebiet': 'Innenpolitik',
            'organisation': 'CDU/CSU-Fraktion', 'person': 'Dr. Friedrich Merz'}, {'organisation':
            'SPD-Fraktion'}], 'kurztitel': 'Wahlrechtsreform', 'links':
            ['https://www.bundestag.de/dokumente/textarchiv/2024/wahlrechtsreform',
            'https://dip.bundestag.de/vorgang/123456'], 'lobbyregister': [{'betroffene_drucksachen':
            ['BT-Drs. 20/12345'], 'intention': 'Stellungnahme zu Auswirkungen der Gesetzesänderung auf
            die deutsche Wirtschaft.', 'interne_id': 'LR-ID-12345678', 'link':
            'https://www.lobbyregister.bundestag.de/eintragung/12345678', 'organisation':
            {'organisation': 'Bundesverband der Deutschen Industrie e.V.', 'person': 'Dr. Johannes
            Weber'}}], 'stationen': [{'api_id': 'f1e2d3c4-b5a6-7890-abcd-1234567890cd', 'dokumente':
            [], 'parlament': 'BT', 'titel': 'Erste Lesung im Bundestag', 'typ': 'parl-vollvlsgn',
            'zp_modifiziert': '2024-04-15T13:45:00+02:00', 'zp_start': '2024-04-15T10:00:00+02:00'}],
            'titel': 'Gesetz zur Änderung des Bundeswahlgesetzes und anderer Gesetze', 'typ': 'gg-
            einspruch', 'verfassungsaendernd': False, 'wahlperiode': 20}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        vorgang_id=vorgang_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    vorgang_id: UUID,
    *,
    client: AuthenticatedClient,
    body: Vorgang,
) -> Response[Any]:
    """Administrative endpoint to directly set or replace a legislative process without merging or
    matching. Replaces the entire process data if it exists, or creates a new one if it doesn't.

    Args:
        vorgang_id (UUID):
        body (Vorgang): 'Master-Objekt' der API. Der Wrapper um Stationen, die den
            Beratungsverlauf tatsächlich beschreiben. Ein Vorgang kann dabei nicht nur ein Gesetz,
            sondern auch ein parlamentarischer Antrag sein. Example: {'api_id':
            '123e4567-e89b-12d3-a456-426614174000', 'ids': [{'id': '20/12345', 'typ': 'initdrucks'},
            {'id': 'WR-2024-01', 'typ': 'vorgnr'}], 'initiatoren': [{'fachgebiet': 'Innenpolitik',
            'organisation': 'CDU/CSU-Fraktion', 'person': 'Dr. Friedrich Merz'}, {'organisation':
            'SPD-Fraktion'}], 'kurztitel': 'Wahlrechtsreform', 'links':
            ['https://www.bundestag.de/dokumente/textarchiv/2024/wahlrechtsreform',
            'https://dip.bundestag.de/vorgang/123456'], 'lobbyregister': [{'betroffene_drucksachen':
            ['BT-Drs. 20/12345'], 'intention': 'Stellungnahme zu Auswirkungen der Gesetzesänderung auf
            die deutsche Wirtschaft.', 'interne_id': 'LR-ID-12345678', 'link':
            'https://www.lobbyregister.bundestag.de/eintragung/12345678', 'organisation':
            {'organisation': 'Bundesverband der Deutschen Industrie e.V.', 'person': 'Dr. Johannes
            Weber'}}], 'stationen': [{'api_id': 'f1e2d3c4-b5a6-7890-abcd-1234567890cd', 'dokumente':
            [], 'parlament': 'BT', 'titel': 'Erste Lesung im Bundestag', 'typ': 'parl-vollvlsgn',
            'zp_modifiziert': '2024-04-15T13:45:00+02:00', 'zp_start': '2024-04-15T10:00:00+02:00'}],
            'titel': 'Gesetz zur Änderung des Bundeswahlgesetzes und anderer Gesetze', 'typ': 'gg-
            einspruch', 'verfassungsaendernd': False, 'wahlperiode': 20}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        vorgang_id=vorgang_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
