from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.parlament import Parlament
from ..types import UNSET, Unset

T = TypeVar("T", bound="ReplacementPutRequestInnerGremiumValuesItem")


@_attrs_define
class ReplacementPutRequestInnerGremiumValuesItem:
    """A body in which decisions can be made: committees, plenary halls, cabinett, peoples, ...

    Attributes:
        name (str): Name of the body. 'plenum', 'regierung', 'volk' are reserved
        parlament (Parlament): Enumeration of parliaments or similar bodies in germany
        wahlperiode (int):
        link (None | str | Unset):
    """

    name: str
    parlament: Parlament
    wahlperiode: int
    link: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        parlament = self.parlament.value

        wahlperiode = self.wahlperiode

        link: None | str | Unset
        if isinstance(self.link, Unset):
            link = UNSET
        else:
            link = self.link

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "parlament": parlament,
                "wahlperiode": wahlperiode,
            }
        )
        if link is not UNSET:
            field_dict["link"] = link

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        parlament = Parlament(d.pop("parlament"))

        wahlperiode = d.pop("wahlperiode")

        def _parse_link(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        link = _parse_link(d.pop("link", UNSET))

        replacement_put_request_inner_gremium_values_item = cls(
            name=name,
            parlament=parlament,
            wahlperiode=wahlperiode,
            link=link,
        )

        replacement_put_request_inner_gremium_values_item.additional_properties = d
        return replacement_put_request_inner_gremium_values_item

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
