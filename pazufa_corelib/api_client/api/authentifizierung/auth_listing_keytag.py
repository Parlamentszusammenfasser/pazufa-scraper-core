from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.keytag_listing import KeytagListing
from ...types import Response


def _get_kwargs(
    keytag: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/auth/keys/{keytag}".format(
            keytag=quote(str(keytag), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | KeytagListing | str | None:
    if response.status_code == 200:
        response_200 = KeytagListing.from_dict(response.json())

        return response_200

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
) -> Response[Any | KeytagListing | str]:
    """
    Args:
        keytag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | KeytagListing | str]
    """

    kwargs = _get_kwargs(
        keytag=keytag,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    keytag: str,
    *,
    client: AuthenticatedClient,
) -> Any | KeytagListing | str | None:
    """
    Args:
        keytag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | KeytagListing | str
    """

    return sync_detailed(
        keytag=keytag,
        client=client,
    ).parsed


async def asyncio_detailed(
    keytag: str,
    *,
    client: AuthenticatedClient,
) -> Response[Any | KeytagListing | str]:
    """
    Args:
        keytag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | KeytagListing | str]
    """

    kwargs = _get_kwargs(
        keytag=keytag,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    keytag: str,
    *,
    client: AuthenticatedClient,
) -> Any | KeytagListing | str | None:
    """
    Args:
        keytag (str):

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
        )
    ).parsed
