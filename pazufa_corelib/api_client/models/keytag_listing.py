from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="KeytagListing")


@_attrs_define
class KeytagListing:
    """
    Attributes:
        dokumente (list[str] | None | Unset):
        sitzungen (list[str] | None | Unset):
        stationen (list[str] | None | Unset):
        vorgaenge (list[str] | None | Unset):
    """

    dokumente: list[str] | None | Unset = UNSET
    sitzungen: list[str] | None | Unset = UNSET
    stationen: list[str] | None | Unset = UNSET
    vorgaenge: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        dokumente: list[str] | None | Unset
        if isinstance(self.dokumente, Unset):
            dokumente = UNSET
        elif isinstance(self.dokumente, list):
            dokumente = self.dokumente

        else:
            dokumente = self.dokumente

        sitzungen: list[str] | None | Unset
        if isinstance(self.sitzungen, Unset):
            sitzungen = UNSET
        elif isinstance(self.sitzungen, list):
            sitzungen = self.sitzungen

        else:
            sitzungen = self.sitzungen

        stationen: list[str] | None | Unset
        if isinstance(self.stationen, Unset):
            stationen = UNSET
        elif isinstance(self.stationen, list):
            stationen = self.stationen

        else:
            stationen = self.stationen

        vorgaenge: list[str] | None | Unset
        if isinstance(self.vorgaenge, Unset):
            vorgaenge = UNSET
        elif isinstance(self.vorgaenge, list):
            vorgaenge = self.vorgaenge

        else:
            vorgaenge = self.vorgaenge

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if dokumente is not UNSET:
            field_dict["dokumente"] = dokumente
        if sitzungen is not UNSET:
            field_dict["sitzungen"] = sitzungen
        if stationen is not UNSET:
            field_dict["stationen"] = stationen
        if vorgaenge is not UNSET:
            field_dict["vorgaenge"] = vorgaenge

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_dokumente(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                dokumente_type_0 = cast(list[str], data)

                return dokumente_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        dokumente = _parse_dokumente(d.pop("dokumente", UNSET))

        def _parse_sitzungen(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                sitzungen_type_0 = cast(list[str], data)

                return sitzungen_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        sitzungen = _parse_sitzungen(d.pop("sitzungen", UNSET))

        def _parse_stationen(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                stationen_type_0 = cast(list[str], data)

                return stationen_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        stationen = _parse_stationen(d.pop("stationen", UNSET))

        def _parse_vorgaenge(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                vorgaenge_type_0 = cast(list[str], data)

                return vorgaenge_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        vorgaenge = _parse_vorgaenge(d.pop("vorgaenge", UNSET))

        keytag_listing = cls(
            dokumente=dokumente,
            sitzungen=sitzungen,
            stationen=stationen,
            vorgaenge=vorgaenge,
        )

        keytag_listing.additional_properties = d
        return keytag_listing

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
