import datetime
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.parlament import Parlament
from ...models.sitzung import Sitzung
from ...types import UNSET, Response, Unset


def _get_kwargs(
    parlament: Parlament,
    datum: datetime.date,
    *,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    if_modified_since: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_modified_since, Unset):
        headers["If-Modified-Since"] = if_modified_since

    params: dict[str, Any] = {}

    params["page"] = page

    params["per_page"] = per_page

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/kalender/{parlament}/{datum}".format(
            parlament=quote(str(parlament), safe=""),
            datum=quote(str(datum), safe=""),
        ),
        "params": params,
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | list[Sitzung] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = Sitzung.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 404:
        response_404 = cast(Any, None)
        return response_404

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | list[Sitzung]]:
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
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    if_modified_since: str | Unset = UNSET,
) -> Response[Any | list[Sitzung]]:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        datum (datetime.date):
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[Sitzung]]
    """

    kwargs = _get_kwargs(
        parlament=parlament,
        datum=datum,
        page=page,
        per_page=per_page,
        if_modified_since=if_modified_since,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    if_modified_since: str | Unset = UNSET,
) -> Any | list[Sitzung] | None:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        datum (datetime.date):
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[Sitzung]
    """

    return sync_detailed(
        parlament=parlament,
        datum=datum,
        client=client,
        page=page,
        per_page=per_page,
        if_modified_since=if_modified_since,
    ).parsed


async def asyncio_detailed(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    if_modified_since: str | Unset = UNSET,
) -> Response[Any | list[Sitzung]]:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        datum (datetime.date):
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[Sitzung]]
    """

    kwargs = _get_kwargs(
        parlament=parlament,
        datum=datum,
        page=page,
        per_page=per_page,
        if_modified_since=if_modified_since,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    if_modified_since: str | Unset = UNSET,
) -> Any | list[Sitzung] | None:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        datum (datetime.date):
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[Sitzung]
    """

    return (
        await asyncio_detailed(
            parlament=parlament,
            datum=datum,
            client=client,
            page=page,
            per_page=per_page,
            if_modified_since=if_modified_since,
        )
    ).parsed
