from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Zusammenfassungstupel")


@_attrs_define
class Zusammenfassungstupel:
    """A typed partial summary of a document.
    NOTE: Documents can only contain one summary of any type.
    If on merge a different text is supplied for an existing type of summary, it replaces the old
    one

        Attributes:
            inhalt (str | Unset): Content of the summary part Example: Das Gesetz zur Haarfärbeverordnung dient der
                Umsetzung der EU-Richtline 42/69420 zur Schuppenfreiheit bei Eigenschaftsänderlichen Haarmodifikationen vor....
            typ (str | Unset): Type of summary, if the summary is made up of parts
                NOTE: there are some reserved type names:
                - `full`        means summary of the full document without origin info
                - `full-llm`    means summary of the full document, made by llm
                - `full-extern` means summary of the full document, taken from an external source

                You are free to add to these if required, just please stick to the ones available if
                possible Example: Basisinformationen.
    """

    inhalt: str | Unset = UNSET
    typ: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        inhalt = self.inhalt

        typ = self.typ

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if inhalt is not UNSET:
            field_dict["inhalt"] = inhalt
        if typ is not UNSET:
            field_dict["typ"] = typ

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        inhalt = d.pop("inhalt", UNSET)

        typ = d.pop("typ", UNSET)

        zusammenfassungstupel = cls(
            inhalt=inhalt,
            typ=typ,
        )

        zusammenfassungstupel.additional_properties = d
        return zusammenfassungstupel

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
