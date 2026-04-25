from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.gremium import Gremium


T = TypeVar("T", bound="GremienPutBodyReplacingItem")


@_attrs_define
class GremienPutBodyReplacingItem:
    """
    Attributes:
        replaced_by (int): This object is replaced by the object with index {} in the 'objects' list above. 0-Based
            indexing.
        values (list[Gremium]):
    """

    replaced_by: int
    values: list[Gremium]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        replaced_by = self.replaced_by

        values = []
        for values_item_data in self.values:
            values_item = values_item_data.to_dict()
            values.append(values_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "replaced_by": replaced_by,
                "values": values,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.gremium import Gremium

        d = dict(src_dict)
        replaced_by = d.pop("replaced_by")

        values = []
        _values = d.pop("values")
        for values_item_data in _values:
            values_item = Gremium.from_dict(values_item_data)

            values.append(values_item)

        gremien_put_body_replacing_item = cls(
            replaced_by=replaced_by,
            values=values,
        )

        gremien_put_body_replacing_item.additional_properties = d
        return gremien_put_body_replacing_item

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
