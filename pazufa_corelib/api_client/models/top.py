from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.dokument import Dokument


T = TypeVar("T", bound="Top")


@_attrs_define
class Top:
    """An item on the agenda

    Attributes:
        nummer (int): number of this item on the agenda
        titel (str):
        dokumente (list[Dokument | UUID] | Unset): documents handled in this agenda item
        vorgang_id (list[UUID] | Unset): api ids of associated Vorgang objects.
            Is ignored at upload time, but passed at download time.
            The matching happens via the documents supplied below
    """

    nummer: int
    titel: str
    dokumente: list[Dokument | UUID] | Unset = UNSET
    vorgang_id: list[UUID] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.dokument import Dokument

        nummer = self.nummer

        titel = self.titel

        dokumente: list[dict[str, Any] | str] | Unset = UNSET
        if not isinstance(self.dokumente, Unset):
            dokumente = []
            for dokumente_item_data in self.dokumente:
                dokumente_item: dict[str, Any] | str
                if isinstance(dokumente_item_data, Dokument):
                    dokumente_item = dokumente_item_data.to_dict()
                else:
                    dokumente_item = str(dokumente_item_data)

                dokumente.append(dokumente_item)

        vorgang_id: list[str] | Unset = UNSET
        if not isinstance(self.vorgang_id, Unset):
            vorgang_id = []
            for vorgang_id_item_data in self.vorgang_id:
                vorgang_id_item = str(vorgang_id_item_data)
                vorgang_id.append(vorgang_id_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nummer": nummer,
                "titel": titel,
            }
        )
        if dokumente is not UNSET:
            field_dict["dokumente"] = dokumente
        if vorgang_id is not UNSET:
            field_dict["vorgang_id"] = vorgang_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dokument import Dokument

        d = dict(src_dict)
        nummer = d.pop("nummer")

        titel = d.pop("titel")

        _dokumente = d.pop("dokumente", UNSET)
        dokumente: list[Dokument | UUID] | Unset = UNSET
        if _dokumente is not UNSET:
            dokumente = []
            for dokumente_item_data in _dokumente:

                def _parse_dokumente_item(data: object) -> Dokument | UUID:
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        componentsschemas_dokument_or_api_id_type_0 = Dokument.from_dict(data)

                        return componentsschemas_dokument_or_api_id_type_0
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    if not isinstance(data, str):
                        raise TypeError()
                    componentsschemas_dokument_or_api_id_type_1 = UUID(data)

                    return componentsschemas_dokument_or_api_id_type_1

                dokumente_item = _parse_dokumente_item(dokumente_item_data)

                dokumente.append(dokumente_item)

        _vorgang_id = d.pop("vorgang_id", UNSET)
        vorgang_id: list[UUID] | Unset = UNSET
        if _vorgang_id is not UNSET:
            vorgang_id = []
            for vorgang_id_item_data in _vorgang_id:
                vorgang_id_item = UUID(vorgang_id_item_data)

                vorgang_id.append(vorgang_id_item)

        top = cls(
            nummer=nummer,
            titel=titel,
            dokumente=dokumente,
            vorgang_id=vorgang_id,
        )

        top.additional_properties = d
        return top

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
