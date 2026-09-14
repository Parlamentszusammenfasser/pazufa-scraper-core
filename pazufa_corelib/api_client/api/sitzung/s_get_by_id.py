from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.sitzung import Sitzung
from ...types import UNSET, Response, Unset


def _get_kwargs(
    api_id: UUID,
    *,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_modified_since, Unset):
        headers["if-modified-since"] = if_modified_since

    params: dict[str, Any] = {}

    params["expand"] = expand

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/sitzung/{api_id}".format(
            api_id=quote(str(api_id), safe=""),
        ),
        "params": params,
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | Sitzung | str | None:
    if response.status_code == 200:
        response_200 = Sitzung.from_dict(response.json())

        return response_200

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 404:
        response_404 = cast(Any, None)
        return response_404

    if response.status_code == 500:
        response_500 = response.text
        return response_500

    if response.status_code == 501:
        response_501 = cast(Any, None)
        return response_501

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | Sitzung | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Response[Any | Sitzung | str]:
    """Retrieves detailed information about a specific parliamentary session by its unique identifier.
    Returns complete session data including agenda items, documents, and metadata. If called by admin or
    higher, this returns a list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Sitzung | str]
    """

    kwargs = _get_kwargs(
        api_id=api_id,
        expand=expand,
        if_modified_since=if_modified_since,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Any | Sitzung | str | None:
    """Retrieves detailed information about a specific parliamentary session by its unique identifier.
    Returns complete session data including agenda items, documents, and metadata. If called by admin or
    higher, this returns a list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Sitzung | str
    """

    return sync_detailed(
        api_id=api_id,
        client=client,
        expand=expand,
        if_modified_since=if_modified_since,
    ).parsed


async def asyncio_detailed(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Response[Any | Sitzung | str]:
    """Retrieves detailed information about a specific parliamentary session by its unique identifier.
    Returns complete session data including agenda items, documents, and metadata. If called by admin or
    higher, this returns a list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Sitzung | str]
    """

    kwargs = _get_kwargs(
        api_id=api_id,
        expand=expand,
        if_modified_since=if_modified_since,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Any | Sitzung | str | None:
    """Retrieves detailed information about a specific parliamentary session by its unique identifier.
    Returns complete session data including agenda items, documents, and metadata. If called by admin or
    higher, this returns a list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Sitzung | str
    """

    return (
        await asyncio_detailed(
            api_id=api_id,
            client=client,
            expand=expand,
            if_modified_since=if_modified_since,
        )
    ).parsed
