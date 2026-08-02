import datetime
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.parlament import Parlament
from ...models.sitzung import Sitzung
from ...types import Response


def _get_kwargs(
    parlament: Parlament,
    datum: datetime.date,
    *,
    body: list[Sitzung],
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v2/kalender/{parlament}/{datum}".format(
            parlament=quote(str(parlament), safe=""),
            datum=quote(str(datum), safe=""),
        ),
    }

    _kwargs["json"] = []
    for body_item_data in body:
        body_item = body_item_data.to_dict()
        _kwargs["json"].append(body_item)

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | str | None:
    if response.status_code == 201:
        response_201 = cast(Any, None)
        return response_201

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 400:
        response_400 = response.text
        return response_400

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 409:
        response_409 = cast(Any, None)
        return response_409

    if response.status_code == 500:
        response_500 = response.text
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient,
    body: list[Sitzung],
) -> Response[Any | str]:
    """Collector interface for adding or updating sessions for a specific date and parliament. Completely
    replaces all sessions for the given date, with restrictions based on how far in the past the date
    is. Admin API keys can override the time restriction.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        body (list[Sitzung]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        parlament=parlament,
        datum=datum,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient,
    body: list[Sitzung],
) -> Any | str | None:
    """Collector interface for adding or updating sessions for a specific date and parliament. Completely
    replaces all sessions for the given date, with restrictions based on how far in the past the date
    is. Admin API keys can override the time restriction.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        body (list[Sitzung]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return sync_detailed(
        parlament=parlament,
        datum=datum,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient,
    body: list[Sitzung],
) -> Response[Any | str]:
    """Collector interface for adding or updating sessions for a specific date and parliament. Completely
    replaces all sessions for the given date, with restrictions based on how far in the past the date
    is. Admin API keys can override the time restriction.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        body (list[Sitzung]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        parlament=parlament,
        datum=datum,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient,
    body: list[Sitzung],
) -> Any | str | None:
    """Collector interface for adding or updating sessions for a specific date and parliament. Completely
    replaces all sessions for the given date, with restrictions based on how far in the past the date
    is. Admin API keys can override the time restriction.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        body (list[Sitzung]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return (
        await asyncio_detailed(
            parlament=parlament,
            datum=datum,
            client=client,
            body=body,
        )
    ).parsed
