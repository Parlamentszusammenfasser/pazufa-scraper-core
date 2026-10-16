from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.auth_status_response_200 import AuthStatusResponse200
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    if_none_match: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_none_match, Unset):
        headers["if-none-match"] = if_none_match

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/auth/status",
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | AuthStatusResponse200 | str | None:
    if response.status_code == 200:
        response_200 = AuthStatusResponse200.from_dict(response.json())

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
) -> Response[Any | AuthStatusResponse200 | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Response[Any | AuthStatusResponse200 | str]:
    """Get some information about your own key

    Args:
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | AuthStatusResponse200 | str]
    """

    kwargs = _get_kwargs(
        if_none_match=if_none_match,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Any | AuthStatusResponse200 | str | None:
    """Get some information about your own key

    Args:
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | AuthStatusResponse200 | str
    """

    return sync_detailed(
        client=client,
        if_none_match=if_none_match,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Response[Any | AuthStatusResponse200 | str]:
    """Get some information about your own key

    Args:
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | AuthStatusResponse200 | str]
    """

    kwargs = _get_kwargs(
        if_none_match=if_none_match,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    if_none_match: str | Unset = UNSET,
) -> Any | AuthStatusResponse200 | str | None:
    """Get some information about your own key

    Args:
        if_none_match (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | AuthStatusResponse200 | str
    """

    return (
        await asyncio_detailed(
            client=client,
            if_none_match=if_none_match,
        )
    ).parsed
