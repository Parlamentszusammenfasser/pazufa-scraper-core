from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.vorgang import Vorgang
from ...types import UNSET, Response, Unset


def _get_kwargs(
    vorgang_id: UUID,
    *,
    if_modified_since: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_modified_since, Unset):
        headers["If-Modified-Since"] = if_modified_since

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/vorgang/{vorgang_id}".format(
            vorgang_id=quote(str(vorgang_id), safe=""),
        ),
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | Vorgang | None:
    if response.status_code == 200:
        response_200 = Vorgang.from_dict(response.json())

        return response_200

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | Vorgang]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    vorgang_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    if_modified_since: str | Unset = UNSET,
) -> Response[Any | Vorgang]:
    """Retrieves a specific legislative process by its unique identifier. Returns comprehensive details
    about the process including all its stations, associated documents, and metadata. If called by admin
    or higher, this returns a list of last scrapers/collectors touching the object

    Args:
        vorgang_id (UUID):
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Vorgang]
    """

    kwargs = _get_kwargs(
        vorgang_id=vorgang_id,
        if_modified_since=if_modified_since,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    vorgang_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    if_modified_since: str | Unset = UNSET,
) -> Any | Vorgang | None:
    """Retrieves a specific legislative process by its unique identifier. Returns comprehensive details
    about the process including all its stations, associated documents, and metadata. If called by admin
    or higher, this returns a list of last scrapers/collectors touching the object

    Args:
        vorgang_id (UUID):
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Vorgang
    """

    return sync_detailed(
        vorgang_id=vorgang_id,
        client=client,
        if_modified_since=if_modified_since,
    ).parsed


async def asyncio_detailed(
    vorgang_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    if_modified_since: str | Unset = UNSET,
) -> Response[Any | Vorgang]:
    """Retrieves a specific legislative process by its unique identifier. Returns comprehensive details
    about the process including all its stations, associated documents, and metadata. If called by admin
    or higher, this returns a list of last scrapers/collectors touching the object

    Args:
        vorgang_id (UUID):
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Vorgang]
    """

    kwargs = _get_kwargs(
        vorgang_id=vorgang_id,
        if_modified_since=if_modified_since,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    vorgang_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    if_modified_since: str | Unset = UNSET,
) -> Any | Vorgang | None:
    """Retrieves a specific legislative process by its unique identifier. Returns comprehensive details
    about the process including all its stations, associated documents, and metadata. If called by admin
    or higher, this returns a list of last scrapers/collectors touching the object

    Args:
        vorgang_id (UUID):
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Vorgang
    """

    return (
        await asyncio_detailed(
            vorgang_id=vorgang_id,
            client=client,
            if_modified_since=if_modified_since,
        )
    ).parsed
