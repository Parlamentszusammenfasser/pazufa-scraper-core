from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.replacement_put_request_inner_gremium_values_item import (
        ReplacementPutRequestInnerGremiumValuesItem,
    )


T = TypeVar("T", bound="ReplacementPutRequestInnerGremium")


@_attrs_define
class ReplacementPutRequestInnerGremium:
    """
    Attributes:
        replaced_by (int): This object is replaced by the object with index {} in the 'objects' list above. 0-Based
            indexing.
        values (list[ReplacementPutRequestInnerGremiumValuesItem]):
    """

    replaced_by: int
    values: list[ReplacementPutRequestInnerGremiumValuesItem]
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
        from ..models.replacement_put_request_inner_gremium_values_item import (
            ReplacementPutRequestInnerGremiumValuesItem,
        )

        d = dict(src_dict)
        replaced_by = d.pop("replaced_by")

        values = []
        _values = d.pop("values")
        for values_item_data in _values:
            values_item = ReplacementPutRequestInnerGremiumValuesItem.from_dict(values_item_data)

            values.append(values_item)

        replacement_put_request_inner_gremium = cls(
            replaced_by=replaced_by,
            values=values,
        )

        replacement_put_request_inner_gremium.additional_properties = d
        return replacement_put_request_inner_gremium

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
