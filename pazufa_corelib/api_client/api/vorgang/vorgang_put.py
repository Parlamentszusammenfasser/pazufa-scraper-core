from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.vorgang import Vorgang
from ...types import Response


def _get_kwargs(
    *,
    body: Vorgang,
    x_scraper_id: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["x-scraper-id"] = x_scraper_id

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v2/vorgang",
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
    *,
    client: AuthenticatedClient,
    body: Vorgang,
    x_scraper_id: str,
) -> Response[Any | str]:
    """Collector interface for inserting a new legislative process. Processes are automatically
    deduplicated against existing data and merged if necessary. Used by data collection services to add
    new legislative processes to the system.

    Args:
        x_scraper_id (str):
        body (Vorgang): 'Master Object of the API. Wrapper type around stations.
            `Vorgang` describes not only legislative processes, but also other kinds of parliamentary
            proceedings

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        body=body,
        x_scraper_id=x_scraper_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: Vorgang,
    x_scraper_id: str,
) -> Any | str | None:
    """Collector interface for inserting a new legislative process. Processes are automatically
    deduplicated against existing data and merged if necessary. Used by data collection services to add
    new legislative processes to the system.

    Args:
        x_scraper_id (str):
        body (Vorgang): 'Master Object of the API. Wrapper type around stations.
            `Vorgang` describes not only legislative processes, but also other kinds of parliamentary
            proceedings

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return sync_detailed(
        client=client,
        body=body,
        x_scraper_id=x_scraper_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: Vorgang,
    x_scraper_id: str,
) -> Response[Any | str]:
    """Collector interface for inserting a new legislative process. Processes are automatically
    deduplicated against existing data and merged if necessary. Used by data collection services to add
    new legislative processes to the system.

    Args:
        x_scraper_id (str):
        body (Vorgang): 'Master Object of the API. Wrapper type around stations.
            `Vorgang` describes not only legislative processes, but also other kinds of parliamentary
            proceedings

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        body=body,
        x_scraper_id=x_scraper_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: Vorgang,
    x_scraper_id: str,
) -> Any | str | None:
    """Collector interface for inserting a new legislative process. Processes are automatically
    deduplicated against existing data and merged if necessary. Used by data collection services to add
    new legislative processes to the system.

    Args:
        x_scraper_id (str):
        body (Vorgang): 'Master Object of the API. Wrapper type around stations.
            `Vorgang` describes not only legislative processes, but also other kinds of parliamentary
            proceedings

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            x_scraper_id=x_scraper_id,
        )
    ).parsed
