from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.hash_strategy import HashStrategy
from ..models.mime import Mime

T = TypeVar("T", bound="DokumentHash")


@_attrs_define
class DokumentHash:
    """
    Attributes:
        mime (Mime):
        strategy (HashStrategy):
        value (str): Hash value as string of hexadecimal octets
    """

    mime: Mime
    strategy: HashStrategy
    value: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        mime = self.mime.value

        strategy = self.strategy.value

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "mime": mime,
                "strategy": strategy,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        mime = Mime(d.pop("mime"))

        strategy = HashStrategy(d.pop("strategy"))

        value = d.pop("value")

        dokument_hash = cls(
            mime=mime,
            strategy=strategy,
            value=value,
        )

        dokument_hash.additional_properties = d
        return dokument_hash

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
