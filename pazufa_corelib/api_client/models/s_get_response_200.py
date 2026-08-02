from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.sitzung import Sitzung


T = TypeVar("T", bound="SGetResponse200")


@_attrs_define
class SGetResponse200:
    """
    Attributes:
        body (list[Sitzung]):
        link (str):
        x_page (int):
        x_per_page (int):
        x_total_count (int):
        x_total_pages (int):
    """

    body: list[Sitzung]
    link: str
    x_page: int
    x_per_page: int
    x_total_count: int
    x_total_pages: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        body = []
        for body_item_data in self.body:
            body_item = body_item_data.to_dict()
            body.append(body_item)

        link = self.link

        x_page = self.x_page

        x_per_page = self.x_per_page

        x_total_count = self.x_total_count

        x_total_pages = self.x_total_pages

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "body": body,
                "link": link,
                "x_page": x_page,
                "x_per_page": x_per_page,
                "x_total_count": x_total_count,
                "x_total_pages": x_total_pages,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sitzung import Sitzung

        d = dict(src_dict)
        body = []
        _body = d.pop("body")
        for body_item_data in _body:
            body_item = Sitzung.from_dict(body_item_data)

            body.append(body_item)

        link = d.pop("link")

        x_page = d.pop("x_page")

        x_per_page = d.pop("x_per_page")

        x_total_count = d.pop("x_total_count")

        x_total_pages = d.pop("x_total_pages")

        s_get_response_200 = cls(
            body=body,
            link=link,
            x_page=x_page,
            x_per_page=x_per_page,
            x_total_count=x_total_count,
            x_total_pages=x_total_pages,
        )

        s_get_response_200.additional_properties = d
        return s_get_response_200

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
