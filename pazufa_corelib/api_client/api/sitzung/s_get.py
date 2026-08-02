import datetime
from http import HTTPStatus
from typing import Any, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.parlament import Parlament
from ...models.s_get_response_200 import SGetResponse200
from ...models.vorgangstyp import Vorgangstyp
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(if_modified_since, Unset):
        headers["if_modified_since"] = if_modified_since

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

    params["expand"] = expand

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/sitzung",
        "params": params,
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | SGetResponse200 | str | None:
    if response.status_code == 200:
        response_200 = SGetResponse200.from_dict(response.json())

        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 304:
        response_304 = cast(Any, None)
        return response_304

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 416:
        response_416 = cast(Any, None)
        return response_416

    if response.status_code == 500:
        response_500 = response.text
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | SGetResponse200 | str]:
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
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Response[Any | SGetResponse200 | str]:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        page (int | Unset):
        per_page (int | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | SGetResponse200 | str]
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
        expand=expand,
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
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Any | SGetResponse200 | str | None:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        page (int | Unset):
        per_page (int | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | SGetResponse200 | str
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
        expand=expand,
        if_modified_since=if_modified_since,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Response[Any | SGetResponse200 | str]:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        page (int | Unset):
        per_page (int | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | SGetResponse200 | str]
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
        expand=expand,
        if_modified_since=if_modified_since,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    gr: str | Unset = UNSET,
    vgid: UUID | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    expand: bool | Unset = UNSET,
    if_modified_since: None | str | Unset = UNSET,
) -> Any | SGetResponse200 | str | None:
    """Retrieves a filterable list of parliamentary sessions. Returns up to 64 sessions per request, which
    can be filtered by various criteria including time frame, parliament, and electoral period.

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        page (int | Unset):
        per_page (int | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        gr (str | Unset):
        vgid (UUID | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        expand (bool | Unset):
        if_modified_since (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | SGetResponse200 | str
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
            expand=expand,
            if_modified_since=if_modified_since,
        )
    ).parsed
