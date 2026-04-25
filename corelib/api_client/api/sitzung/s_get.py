import datetime
from http import HTTPStatus
from typing import Any, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.parlament import Parlament
from ...models.sitzung import Sitzung
from ...models.vorgangstyp import Vorgangstyp
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    if_modified_since: str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_modified_since, Unset):
        headers["If-Modified-Since"] = if_modified_since

    params: dict[str, Any] = {}

    json_since: str | Unset = UNSET
    if not isinstance(since, Unset):
        json_since = since.isoformat()
    params["since"] = json_since

    json_until: str | Unset = UNSET
    if not isinstance(until, Unset):
        json_until = until.isoformat()
    params["until"] = json_until

    params["page"] = page

    params["per_page"] = per_page

    json_p: str | Unset = UNSET
    if not isinstance(p, Unset):
        json_p = p.value

    params["p"] = json_p

    params["wp"] = wp

    params["gr"] = gr

    json_vgid: str | Unset = UNSET
    if not isinstance(vgid, Unset):
        json_vgid = str(vgid)
    params["vgid"] = json_vgid

    json_vgtyp: str | Unset = UNSET
    if not isinstance(vgtyp, Unset):
        json_vgtyp = vgtyp.value

    params["vgtyp"] = json_vgtyp

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/sitzung",
        "params": params,
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | list[Sitzung] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = Sitzung.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 416:
        response_416 = cast(Any, None)
        return response_416

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | list[Sitzung]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    if_modified_since: str | Unset = UNSET,
) -> Response[Any | list[Sitzung]]:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):  Example: 2024-01-01T00:00:00+00:00.
        until (datetime.datetime | Unset):  Example: 2024-12-31T23:59:59+00:00.
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        p (Parlament | Unset): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): Der Gesetzgebungstrack auf dem wir uns befinden. Zum
            Beispiel: gesetzgebung - Einspruchsgesetz. Legt fest, welche Stationen im Vorgang möglich
            sind zusammen mit den Parlamenten in den Stationen
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[Sitzung]]
    """

    kwargs = _get_kwargs(
        since=since,
        until=until,
        page=page,
        per_page=per_page,
        p=p,
        wp=wp,
        gr=gr,
        vgid=vgid,
        vgtyp=vgtyp,
        if_modified_since=if_modified_since,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    if_modified_since: str | Unset = UNSET,
) -> Any | list[Sitzung] | None:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):  Example: 2024-01-01T00:00:00+00:00.
        until (datetime.datetime | Unset):  Example: 2024-12-31T23:59:59+00:00.
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        p (Parlament | Unset): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): Der Gesetzgebungstrack auf dem wir uns befinden. Zum
            Beispiel: gesetzgebung - Einspruchsgesetz. Legt fest, welche Stationen im Vorgang möglich
            sind zusammen mit den Parlamenten in den Stationen
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[Sitzung]
    """

    return sync_detailed(
        client=client,
        since=since,
        until=until,
        page=page,
        per_page=per_page,
        p=p,
        wp=wp,
        gr=gr,
        vgid=vgid,
        vgtyp=vgtyp,
        if_modified_since=if_modified_since,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    if_modified_since: str | Unset = UNSET,
) -> Response[Any | list[Sitzung]]:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):  Example: 2024-01-01T00:00:00+00:00.
        until (datetime.datetime | Unset):  Example: 2024-12-31T23:59:59+00:00.
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        p (Parlament | Unset): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): Der Gesetzgebungstrack auf dem wir uns befinden. Zum
            Beispiel: gesetzgebung - Einspruchsgesetz. Legt fest, welche Stationen im Vorgang möglich
            sind zusammen mit den Parlamenten in den Stationen
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[Sitzung]]
    """

    kwargs = _get_kwargs(
        since=since,
        until=until,
        page=page,
        per_page=per_page,
        p=p,
        wp=wp,
        gr=gr,
        vgid=vgid,
        vgtyp=vgtyp,
        if_modified_since=if_modified_since,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = 1,
    per_page: int | Unset = 32,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    if_modified_since: str | Unset = UNSET,
) -> Any | list[Sitzung] | None:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):  Example: 2024-01-01T00:00:00+00:00.
        until (datetime.datetime | Unset):  Example: 2024-12-31T23:59:59+00:00.
        page (int | Unset):  Default: 1.
        per_page (int | Unset):  Default: 32.
        p (Parlament | Unset): Enumeration der Parlamentsähnlichen Entscheidungscorpi in
            Deutschland
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): Der Gesetzgebungstrack auf dem wir uns befinden. Zum
            Beispiel: gesetzgebung - Einspruchsgesetz. Legt fest, welche Stationen im Vorgang möglich
            sind zusammen mit den Parlamenten in den Stationen
        if_modified_since (str | Unset):  Example: 2024-01-01T00:00:00+00:00.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[Sitzung]
    """

    return (
        await asyncio_detailed(
            client=client,
            since=since,
            until=until,
            page=page,
            per_page=per_page,
            p=p,
            wp=wp,
            gr=gr,
            vgid=vgid,
            vgtyp=vgtyp,
            if_modified_since=if_modified_since,
        )
    ).parsed
