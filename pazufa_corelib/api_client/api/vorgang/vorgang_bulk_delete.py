import datetime
from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.parlament import Parlament
from ...models.vorgangstyp import Vorgangstyp
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_since: str | Unset = UNSET
    if not isinstance(since, Unset):
        json_since = since.isoformat()
    params["since"] = json_since

    json_until: str | Unset = UNSET
    if not isinstance(until, Unset):
        json_until = until.isoformat()
    params["until"] = json_until

    json_p: str | Unset = UNSET
    if not isinstance(p, Unset):
        json_p = p.value

    params["p"] = json_p

    params["wp"] = wp

    params["person"] = person

    params["fach"] = fach

    params["org"] = org

    json_vgtyp: str | Unset = UNSET
    if not isinstance(vgtyp, Unset):
        json_vgtyp = vgtyp.value

    params["vgtyp"] = json_vgtyp

    params["page"] = page

    params["per_page"] = per_page

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/v2/vorgang",
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
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
) -> Response[Any | str]:
    """Administrative endpoint to delete Vorgang objects from the system by filter parmeters. This
    operation cannot be undone. With Empty Filters, this is a NOOP

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        page (int | Unset):
        per_page (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        since=since,
        until=until,
        p=p,
        wp=wp,
        person=person,
        fach=fach,
        org=org,
        vgtyp=vgtyp,
        page=page,
        per_page=per_page,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
) -> Any | str | None:
    """Administrative endpoint to delete Vorgang objects from the system by filter parmeters. This
    operation cannot be undone. With Empty Filters, this is a NOOP

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        page (int | Unset):
        per_page (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return sync_detailed(
        client=client,
        since=since,
        until=until,
        p=p,
        wp=wp,
        person=person,
        fach=fach,
        org=org,
        vgtyp=vgtyp,
        page=page,
        per_page=per_page,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
) -> Response[Any | str]:
    """Administrative endpoint to delete Vorgang objects from the system by filter parmeters. This
    operation cannot be undone. With Empty Filters, this is a NOOP

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        page (int | Unset):
        per_page (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | str]
    """

    kwargs = _get_kwargs(
        since=since,
        until=until,
        p=p,
        wp=wp,
        person=person,
        fach=fach,
        org=org,
        vgtyp=vgtyp,
        page=page,
        per_page=per_page,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    since: datetime.datetime | Unset = UNSET,
    until: datetime.datetime | Unset = UNSET,
    p: Parlament | Unset = UNSET,
    wp: int | Unset = UNSET,
    person: str | Unset = UNSET,
    fach: str | Unset = UNSET,
    org: str | Unset = UNSET,
    vgtyp: Vorgangstyp | Unset = UNSET,
    page: int | Unset = UNSET,
    per_page: int | Unset = UNSET,
) -> Any | str | None:
    """Administrative endpoint to delete Vorgang objects from the system by filter parmeters. This
    operation cannot be undone. With Empty Filters, this is a NOOP

    Args:
        since (datetime.datetime | Unset):
        until (datetime.datetime | Unset):
        p (Parlament | Unset): Enumeration of parliaments or similar bodies in germany
        wp (int | Unset):
        person (str | Unset):
        fach (str | Unset):
        org (str | Unset):
        vgtyp (Vorgangstyp | Unset): The legislative Track we are on. Together with a parliament,
            this tells us about the possible stations that can occurr within
        page (int | Unset):
        per_page (int | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | str
    """

    return (
        await asyncio_detailed(
            client=client,
            since=since,
            until=until,
            p=p,
            wp=wp,
            person=person,
            fach=fach,
            org=org,
            vgtyp=vgtyp,
            page=page,
            per_page=per_page,
        )
    ).parsed
