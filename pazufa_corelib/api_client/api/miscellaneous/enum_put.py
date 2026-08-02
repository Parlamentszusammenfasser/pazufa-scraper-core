from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.enumeration_names import EnumerationNames
from ...models.replacement_put_request_string import ReplacementPutRequestString
from ...types import Response


def _get_kwargs(
    name: EnumerationNames,
    *,
    body: ReplacementPutRequestString,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v2/enumeration/{name}".format(
            name=quote(str(name), safe=""),
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
    name: EnumerationNames,
    *,
    client: AuthenticatedClient,
    body: ReplacementPutRequestString,
) -> Response[Any | str]:
    """Administrative endpoint to add or update values in a specified enumeration type. Replaces the entire
    set of values for the enumeration.

    Args:
        name (EnumerationNames): Enumeration of values
        body (ReplacementPutRequestString):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        name=name,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    name: EnumerationNames,
    *,
    client: AuthenticatedClient,
    body: ReplacementPutRequestString,
) -> Any | str | None:
    """Administrative endpoint to add or update values in a specified enumeration type. Replaces the entire
    set of values for the enumeration.

    Args:
        name (EnumerationNames): Enumeration of values
        body (ReplacementPutRequestString):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return sync_detailed(
        name=name,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    name: EnumerationNames,
    *,
    client: AuthenticatedClient,
    body: ReplacementPutRequestString,
) -> Response[Any | str]:
    """Administrative endpoint to add or update values in a specified enumeration type. Replaces the entire
    set of values for the enumeration.

    Args:
        name (EnumerationNames): Enumeration of values
        body (ReplacementPutRequestString):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        name=name,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    name: EnumerationNames,
    *,
    client: AuthenticatedClient,
    body: ReplacementPutRequestString,
) -> Any | str | None:
    """Administrative endpoint to add or update values in a specified enumeration type. Replaces the entire
    set of values for the enumeration.

    Args:
        name (EnumerationNames): Enumeration of values
        body (ReplacementPutRequestString):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return (
        await asyncio_detailed(
            name=name,
            client=client,
            body=body,
        )
    ).parsed
