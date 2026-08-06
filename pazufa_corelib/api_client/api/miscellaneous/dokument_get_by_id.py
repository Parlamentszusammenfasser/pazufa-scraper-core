from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.dokument import Dokument
from ...models.dokument_format import DokumentFormat
from ...types import UNSET, Response, Unset


def _get_kwargs(
    api_id: UUID,
    *,
    format_: DokumentFormat | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_format_: str | Unset = UNSET
    if not isinstance(format_, Unset):
        json_format_ = format_.value

    params["format"] = json_format_

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/dokument/{api_id}".format(
            api_id=quote(str(api_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | Dokument | str | None:
    if response.status_code == 200:
        response_200 = Dokument.from_dict(response.json())

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


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | Dokument | str]:
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
    format_: DokumentFormat | Unset = UNSET,
) -> Response[Any | Dokument | str]:
    """Retrieves a specific document by its unique identifier. Returns complete document data including
    title, full text, metadata, and author information. If called by admin or higher, this returns a
    list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        format_ (DokumentFormat | Unset): Format of return of the documents. Defaults to pazufa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Dokument | str]
    """

    kwargs = _get_kwargs(
        api_id=api_id,
        format_=format_,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    format_: DokumentFormat | Unset = UNSET,
) -> Any | Dokument | str | None:
    """Retrieves a specific document by its unique identifier. Returns complete document data including
    title, full text, metadata, and author information. If called by admin or higher, this returns a
    list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        format_ (DokumentFormat | Unset): Format of return of the documents. Defaults to pazufa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Dokument | str
    """

    return sync_detailed(
        api_id=api_id,
        client=client,
        format_=format_,
    ).parsed


async def asyncio_detailed(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    format_: DokumentFormat | Unset = UNSET,
) -> Response[Any | Dokument | str]:
    """Retrieves a specific document by its unique identifier. Returns complete document data including
    title, full text, metadata, and author information. If called by admin or higher, this returns a
    list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        format_ (DokumentFormat | Unset): Format of return of the documents. Defaults to pazufa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Dokument | str]
    """

    kwargs = _get_kwargs(
        api_id=api_id,
        format_=format_,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    api_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    format_: DokumentFormat | Unset = UNSET,
) -> Any | Dokument | str | None:
    """Retrieves a specific document by its unique identifier. Returns complete document data including
    title, full text, metadata, and author information. If called by admin or higher, this returns a
    list of last scrapers/collectors touching the object

    Args:
        api_id (UUID):
        format_ (DokumentFormat | Unset): Format of return of the documents. Defaults to pazufa

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Dokument | str
    """

    return (
        await asyncio_detailed(
            api_id=api_id,
            client=client,
            format_=format_,
        )
    ).parsed
