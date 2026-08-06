from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TouchedByInner")


@_attrs_define
class TouchedByInner:
    """
    Attributes:
        key (None | str | Unset): Key hash of the scraper that touched the object
        scraper_id (None | Unset | UUID): uuid of the scraper that touched this object
    """

    key: None | str | Unset = UNSET
    scraper_id: None | Unset | UUID = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        key: None | str | Unset
        if isinstance(self.key, Unset):
            key = UNSET
        else:
            key = self.key

        scraper_id: None | str | Unset
        if isinstance(self.scraper_id, Unset):
            scraper_id = UNSET
        elif isinstance(self.scraper_id, UUID):
            scraper_id = str(self.scraper_id)
        else:
            scraper_id = self.scraper_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if key is not UNSET:
            field_dict["key"] = key
        if scraper_id is not UNSET:
            field_dict["scraper_id"] = scraper_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_key(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        key = _parse_key(d.pop("key", UNSET))

        def _parse_scraper_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                scraper_id_type_0 = UUID(data)

                return scraper_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        scraper_id = _parse_scraper_id(d.pop("scraper_id", UNSET))

        touched_by_inner = cls(
            key=key,
            scraper_id=scraper_id,
        )

        touched_by_inner.additional_properties = d
        return touched_by_inner

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
