from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Autor")


@_attrs_define
class Autor:
    """Person or organisation in some function. e.g.:
    - authors of a statement,
    - expert at a hearing,
    - initiator of a Vorgang
    - authoring organisations of documents

        Attributes:
            organisation (str):
            fachgebiet (None | str | Unset):
            lobbyregister (None | str | Unset):
            person (None | str | Unset):
    """

    organisation: str
    fachgebiet: None | str | Unset = UNSET
    lobbyregister: None | str | Unset = UNSET
    person: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        organisation = self.organisation

        fachgebiet: None | str | Unset
        if isinstance(self.fachgebiet, Unset):
            fachgebiet = UNSET
        else:
            fachgebiet = self.fachgebiet

        lobbyregister: None | str | Unset
        if isinstance(self.lobbyregister, Unset):
            lobbyregister = UNSET
        else:
            lobbyregister = self.lobbyregister

        person: None | str | Unset
        if isinstance(self.person, Unset):
            person = UNSET
        else:
            person = self.person

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "organisation": organisation,
            }
        )
        if fachgebiet is not UNSET:
            field_dict["fachgebiet"] = fachgebiet
        if lobbyregister is not UNSET:
            field_dict["lobbyregister"] = lobbyregister
        if person is not UNSET:
            field_dict["person"] = person

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        organisation = d.pop("organisation")

        def _parse_fachgebiet(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        fachgebiet = _parse_fachgebiet(d.pop("fachgebiet", UNSET))

        def _parse_lobbyregister(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        lobbyregister = _parse_lobbyregister(d.pop("lobbyregister", UNSET))

        def _parse_person(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        person = _parse_person(d.pop("person", UNSET))

        autor = cls(
            organisation=organisation,
            fachgebiet=fachgebiet,
            lobbyregister=lobbyregister,
            person=person,
        )

        autor.additional_properties = d
        return autor

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
