from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.replacement_put_request_gremium_objects_item import (
        ReplacementPutRequestGremiumObjectsItem,
    )
    from ..models.replacement_put_request_inner_gremium import (
        ReplacementPutRequestInnerGremium,
    )


T = TypeVar("T", bound="ReplacementPutRequestGremium")


@_attrs_define
class ReplacementPutRequestGremium:
    """
    Attributes:
        objects (list[ReplacementPutRequestGremiumObjectsItem]):
        replacing (list[ReplacementPutRequestInnerGremium] | Unset):
    """

    objects: list[ReplacementPutRequestGremiumObjectsItem]
    replacing: list[ReplacementPutRequestInnerGremium] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        objects = []
        for objects_item_data in self.objects:
            objects_item = objects_item_data.to_dict()
            objects.append(objects_item)

        replacing: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.replacing, Unset):
            replacing = []
            for replacing_item_data in self.replacing:
                replacing_item = replacing_item_data.to_dict()
                replacing.append(replacing_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "objects": objects,
            }
        )
        if replacing is not UNSET:
            field_dict["replacing"] = replacing

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.replacement_put_request_gremium_objects_item import (
            ReplacementPutRequestGremiumObjectsItem,
        )
        from ..models.replacement_put_request_inner_gremium import (
            ReplacementPutRequestInnerGremium,
        )

        d = dict(src_dict)
        objects = []
        _objects = d.pop("objects")
        for objects_item_data in _objects:
            objects_item = ReplacementPutRequestGremiumObjectsItem.from_dict(objects_item_data)

            objects.append(objects_item)

        _replacing = d.pop("replacing", UNSET)
        replacing: list[ReplacementPutRequestInnerGremium] | Unset = UNSET
        if _replacing is not UNSET:
            replacing = []
            for replacing_item_data in _replacing:
                replacing_item = ReplacementPutRequestInnerGremium.from_dict(replacing_item_data)

                replacing.append(replacing_item)

        replacement_put_request_gremium = cls(
            objects=objects,
            replacing=replacing,
        )

        replacement_put_request_gremium.additional_properties = d
        return replacement_put_request_gremium

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
