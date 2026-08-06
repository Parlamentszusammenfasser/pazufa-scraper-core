from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.autoren_get_response_200_item import AutorenGetResponse200Item
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    person: None | str | Unset = UNSET,
    fach: None | str | Unset = UNSET,
    org: None | str | Unset = UNSET,
    page: int | None | Unset = UNSET,
    per_page: int | None | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_person: None | str | Unset
    if isinstance(person, Unset):
        json_person = UNSET
    else:
        json_person = person
    params["person"] = json_person

    json_fach: None | str | Unset
    if isinstance(fach, Unset):
        json_fach = UNSET
    else:
        json_fach = fach
    params["fach"] = json_fach

    json_org: None | str | Unset
    if isinstance(org, Unset):
        json_org = UNSET
    else:
        json_org = org
    params["org"] = json_org

    json_page: int | None | Unset
    if isinstance(page, Unset):
        json_page = UNSET
    else:
        json_page = page
    params["page"] = json_page

    json_per_page: int | None | Unset
    if isinstance(per_page, Unset):
        json_per_page = UNSET
    else:
        json_per_page = per_page
    params["per_page"] = json_per_page

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/autoren",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | list[AutorenGetResponse200Item] | str | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = AutorenGetResponse200Item.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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

    if response.status_code == 500:
        response_500 = response.text
        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | list[AutorenGetResponse200Item] | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    person: None | str | Unset = UNSET,
    fach: None | str | Unset = UNSET,
    org: None | str | Unset = UNSET,
    page: int | None | Unset = UNSET,
    per_page: int | None | Unset = UNSET,
) -> Response[Any | list[AutorenGetResponse200Item] | str]:
    """Retrieves a list of authors filtered by optional parameters. Returns authors matching the specified
    criteria including name fragments, professional field, and organization.

    Args:
        person (None | str | Unset):
        fach (None | str | Unset):
        org (None | str | Unset):
        page (int | None | Unset):
        per_page (int | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[AutorenGetResponse200Item] | str]
    """

    kwargs = _get_kwargs(
        person=person,
        fach=fach,
        org=org,
        page=page,
        per_page=per_page,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    person: None | str | Unset = UNSET,
    fach: None | str | Unset = UNSET,
    org: None | str | Unset = UNSET,
    page: int | None | Unset = UNSET,
    per_page: int | None | Unset = UNSET,
) -> Any | list[AutorenGetResponse200Item] | str | None:
    """Retrieves a list of authors filtered by optional parameters. Returns authors matching the specified
    criteria including name fragments, professional field, and organization.

    Args:
        person (None | str | Unset):
        fach (None | str | Unset):
        org (None | str | Unset):
        page (int | None | Unset):
        per_page (int | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[AutorenGetResponse200Item] | str
    """

    return sync_detailed(
        client=client,
        person=person,
        fach=fach,
        org=org,
        page=page,
        per_page=per_page,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    person: None | str | Unset = UNSET,
    fach: None | str | Unset = UNSET,
    org: None | str | Unset = UNSET,
    page: int | None | Unset = UNSET,
    per_page: int | None | Unset = UNSET,
) -> Response[Any | list[AutorenGetResponse200Item] | str]:
    """Retrieves a list of authors filtered by optional parameters. Returns authors matching the specified
    criteria including name fragments, professional field, and organization.

    Args:
        person (None | str | Unset):
        fach (None | str | Unset):
        org (None | str | Unset):
        page (int | None | Unset):
        per_page (int | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | list[AutorenGetResponse200Item] | str]
    """

    kwargs = _get_kwargs(
        person=person,
        fach=fach,
        org=org,
        page=page,
        per_page=per_page,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    person: None | str | Unset = UNSET,
    fach: None | str | Unset = UNSET,
    org: None | str | Unset = UNSET,
    page: int | None | Unset = UNSET,
    per_page: int | None | Unset = UNSET,
) -> Any | list[AutorenGetResponse200Item] | str | None:
    """Retrieves a list of authors filtered by optional parameters. Returns authors matching the specified
    criteria including name fragments, professional field, and organization.

    Args:
        person (None | str | Unset):
        fach (None | str | Unset):
        org (None | str | Unset):
        page (int | None | Unset):
        per_page (int | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | list[AutorenGetResponse200Item] | str
    """

    return (
        await asyncio_detailed(
            client=client,
            person=person,
            fach=fach,
            org=org,
            page=page,
            per_page=per_page,
        )
    ).parsed
