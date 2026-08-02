from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.auth_rotate_response_201 import AuthRotateResponse201
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/auth/rotate",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | AuthRotateResponse201 | str | None:
    if response.status_code == 201:
        response_201 = AuthRotateResponse201.from_dict(response.json())

        return response_201

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
) -> Response[Any | AuthRotateResponse201 | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Any | AuthRotateResponse201 | str]:
    """`AuthRotate` - POST /api/v1/auth/rotate
    Endpoint to rotate your own key for a fresh one. The old key is valid for a certain transition
    period after which it automatically invalidates. If called repeatedly it makes sure that only
    ever a maximum of two (1) keys is valid, a maximum of one of which is in rotation.
    This endpoint requires authentication.
    # Security
    There should always ever be at most two keys in an active rotation relationship (`rotated_for!=NULL`
    && `deleted_by!=NULL`)
    And the rotation date must never be expanded, otherwise you can just prolong your old key's life
    indefinitely

     Key rotation endpoint for creating a new API key while maintaining the existing one for a transition
    period of one day.  The old key remains valid until the specified rotation_complete_date, after
    which it is automatically revoked. Rotates only the own key if it is not invalid.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | AuthRotateResponse201 | str]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> Any | AuthRotateResponse201 | str | None:
    """`AuthRotate` - POST /api/v1/auth/rotate
    Endpoint to rotate your own key for a fresh one. The old key is valid for a certain transition
    period after which it automatically invalidates. If called repeatedly it makes sure that only
    ever a maximum of two (1) keys is valid, a maximum of one of which is in rotation.
    This endpoint requires authentication.
    # Security
    There should always ever be at most two keys in an active rotation relationship (`rotated_for!=NULL`
    && `deleted_by!=NULL`)
    And the rotation date must never be expanded, otherwise you can just prolong your old key's life
    indefinitely

     Key rotation endpoint for creating a new API key while maintaining the existing one for a transition
    period of one day.  The old key remains valid until the specified rotation_complete_date, after
    which it is automatically revoked. Rotates only the own key if it is not invalid.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | AuthRotateResponse201 | str
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Any | AuthRotateResponse201 | str]:
    """`AuthRotate` - POST /api/v1/auth/rotate
    Endpoint to rotate your own key for a fresh one. The old key is valid for a certain transition
    period after which it automatically invalidates. If called repeatedly it makes sure that only
    ever a maximum of two (1) keys is valid, a maximum of one of which is in rotation.
    This endpoint requires authentication.
    # Security
    There should always ever be at most two keys in an active rotation relationship (`rotated_for!=NULL`
    && `deleted_by!=NULL`)
    And the rotation date must never be expanded, otherwise you can just prolong your old key's life
    indefinitely

     Key rotation endpoint for creating a new API key while maintaining the existing one for a transition
    period of one day.  The old key remains valid until the specified rotation_complete_date, after
    which it is automatically revoked. Rotates only the own key if it is not invalid.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | AuthRotateResponse201 | str]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> Any | AuthRotateResponse201 | str | None:
    """`AuthRotate` - POST /api/v1/auth/rotate
    Endpoint to rotate your own key for a fresh one. The old key is valid for a certain transition
    period after which it automatically invalidates. If called repeatedly it makes sure that only
    ever a maximum of two (1) keys is valid, a maximum of one of which is in rotation.
    This endpoint requires authentication.
    # Security
    There should always ever be at most two keys in an active rotation relationship (`rotated_for!=NULL`
    && `deleted_by!=NULL`)
    And the rotation date must never be expanded, otherwise you can just prolong your old key's life
    indefinitely

     Key rotation endpoint for creating a new API key while maintaining the existing one for a transition
    period of one day.  The old key remains valid until the specified rotation_complete_date, after
    which it is automatically revoked. Rotates only the own key if it is not invalid.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | AuthRotateResponse201 | str
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
