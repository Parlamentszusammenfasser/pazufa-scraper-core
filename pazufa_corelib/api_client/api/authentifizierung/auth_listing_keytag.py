from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.keytag_listing import KeytagListing
from ...types import UNSET, Response, Unset


def _get_kwargs(
    keytag: str,
    *,
    if_none_match: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_none_match, Unset):
        headers["if-none-match"] = if_none_match

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/auth/keys/{keytag}".format(
            keytag=quote(str(keytag), safe=""),
        ),
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | KeytagListing | str | None:
    if response.status_code == 200:
        response_200 = KeytagListing.from_dict(response.json())

        return response_200

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 500:
        response_500 = response.text
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | KeytagListing | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    keytag: str,
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Response[Any | KeytagListing | str]:
    """Lists which objects were touched by the supplied keytag

    Args:
        keytag (str):
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | KeytagListing | str]
    """

    kwargs = _get_kwargs(
        keytag=keytag,
        if_none_match=if_none_match,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    keytag: str,
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Any | KeytagListing | str | None:
    """Lists which objects were touched by the supplied keytag

    Args:
        keytag (str):
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | KeytagListing | str
    """

    return sync_detailed(
        keytag=keytag,
        client=client,
        if_none_match=if_none_match,
    ).parsed


async def asyncio_detailed(
    keytag: str,
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Response[Any | KeytagListing | str]:
    """Lists which objects were touched by the supplied keytag

    Args:
        keytag (str):
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | KeytagListing | str]
    """

    kwargs = _get_kwargs(
        keytag=keytag,
        if_none_match=if_none_match,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    keytag: str,
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Any | KeytagListing | str | None:
    """Lists which objects were touched by the supplied keytag

    Args:
        keytag (str):
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | KeytagListing | str
    """

    return (
        await asyncio_detailed(
            keytag=keytag,
            client=client,
            if_none_match=if_none_match,
        )
    ).parsed
