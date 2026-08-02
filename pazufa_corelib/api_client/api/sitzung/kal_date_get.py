import datetime
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.kal_date_get_response_200 import KalDateGetResponse200
from ...models.parlament import Parlament
from ...types import UNSET, Response, Unset


def _get_kwargs(
    parlament: Parlament,
    datum: datetime.date,
    *,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_modified_since, Unset):
        headers["if_modified_since"] = if_modified_since

    params: dict[str, Any] = {}

    params["expand"] = expand

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


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | KalDateGetResponse200 | str | None:
    if response.status_code == 200:
        response_200 = KalDateGetResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 416:
        response_416 = cast(Any, None)
        return response_416

    if response.status_code == 500:
        response_500 = response.text
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | KalDateGetResponse200 | str]:
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
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Response[Any | KalDateGetResponse200 | str]:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | KalDateGetResponse200 | str]
    """

    kwargs = _get_kwargs(
        parlament=parlament,
        datum=datum,
        expand=expand,
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
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Any | KalDateGetResponse200 | str | None:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | KalDateGetResponse200 | str
    """

    return sync_detailed(
        parlament=parlament,
        datum=datum,
        client=client,
        expand=expand,
        if_modified_since=if_modified_since,
    ).parsed


async def asyncio_detailed(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient | Client,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Response[Any | KalDateGetResponse200 | str]:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | KalDateGetResponse200 | str]
    """

    kwargs = _get_kwargs(
        parlament=parlament,
        datum=datum,
        expand=expand,
        if_modified_since=if_modified_since,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    parlament: Parlament,
    datum: datetime.date,
    *,
    client: AuthenticatedClient | Client,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Any | KalDateGetResponse200 | str | None:
    """Retrieves a list of parliamentary sessions for a specific date and parliament. Provides all sessions
    scheduled for the given day in the specified parliamentary body.

    Args:
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        datum (datetime.date):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | KalDateGetResponse200 | str
    """

    return (
        await asyncio_detailed(
            parlament=parlament,
            datum=datum,
            client=client,
            expand=expand,
            if_modified_since=if_modified_since,
        )
    ).parsed
