from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["person"] = person

    params["fach"] = fach

    params["org"] = org

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/v2/autoren",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | str | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 403:
        response_403 = cast(Any, None)
        return response_403

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
    *,
    client: AuthenticatedClient,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
) -> Response[Any | str]:
    """
    Args:
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        person=person,
        fach=fach,
        org=org,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
) -> Any | str | None:
    """
    Args:
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return sync_detailed(
        client=client,
        person=person,
        fach=fach,
        org=org,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
) -> Response[Any | str]:
    """
    Args:
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        person=person,
        fach=fach,
        org=org,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
) -> Any | str | None:
    """
    Args:
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return (
        await asyncio_detailed(
            client=client,
            person=person,
            fach=fach,
            org=org,
        )
    ).parsed
