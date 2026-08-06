from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.dokument import Dokument
from ...types import Response


def _get_kwargs(
    api_id: UUID,
    *,
    body: Dokument,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v2/dokument/{api_id}".format(
            api_id=quote(str(api_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

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
    api_id: UUID,
    *,
    client: AuthenticatedClient,
    body: Dokument,
) -> Response[Any | str]:
    """Administrative endpoint to upload or update documents for future reference. Creates a new document
    with the specified ID or replaces an existing one.

    Args:
        api_id (UUID):
        body (Dokument): A document. Could be a protocol, a Drucksache, a statement, ...
            For different objects, only certain properties are optional, which is a known design flaw.
            A Stellungnahme must contain `meinung`, a Gesetzentwurf contains `Vorwort`.
            Since documents can become quite large, they are returned by the server as just their
            `api_id` in lists

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        api_id=api_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    api_id: UUID,
    *,
    client: AuthenticatedClient,
    body: Dokument,
) -> Any | str | None:
    """Administrative endpoint to upload or update documents for future reference. Creates a new document
    with the specified ID or replaces an existing one.

    Args:
        api_id (UUID):
        body (Dokument): A document. Could be a protocol, a Drucksache, a statement, ...
            For different objects, only certain properties are optional, which is a known design flaw.
            A Stellungnahme must contain `meinung`, a Gesetzentwurf contains `Vorwort`.
            Since documents can become quite large, they are returned by the server as just their
            `api_id` in lists

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return sync_detailed(
        api_id=api_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    api_id: UUID,
    *,
    client: AuthenticatedClient,
    body: Dokument,
) -> Response[Any | str]:
    """Administrative endpoint to upload or update documents for future reference. Creates a new document
    with the specified ID or replaces an existing one.

    Args:
        api_id (UUID):
        body (Dokument): A document. Could be a protocol, a Drucksache, a statement, ...
            For different objects, only certain properties are optional, which is a known design flaw.
            A Stellungnahme must contain `meinung`, a Gesetzentwurf contains `Vorwort`.
            Since documents can become quite large, they are returned by the server as just their
            `api_id` in lists

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        api_id=api_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    api_id: UUID,
    *,
    client: AuthenticatedClient,
    body: Dokument,
) -> Any | str | None:
    """Administrative endpoint to upload or update documents for future reference. Creates a new document
    with the specified ID or replaces an existing one.

    Args:
        api_id (UUID):
        body (Dokument): A document. Could be a protocol, a Drucksache, a statement, ...
            For different objects, only certain properties are optional, which is a known design flaw.
            A Stellungnahme must contain `meinung`, a Gesetzentwurf contains `Vorwort`.
            Since documents can become quite large, they are returned by the server as just their
            `api_id` in lists

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return (
        await asyncio_detailed(
            api_id=api_id,
            client=client,
            body=body,
        )
    ).parsed
