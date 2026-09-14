from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.autor import Autor


T = TypeVar("T", bound="Lobbyregistereintrag")


@_attrs_define
class Lobbyregistereintrag:
    """Entry of the Bundestagslobbyregister for a specific Vorgang

    Attributes:
        betroffene_drucksachen (list[str]): Array with associated Drucksachennummern.
            Is not crossreferenced in the database and just added as dataset
        intention (str): Subject and reason for influencing the legislative process
        interne_id (str): Internal ID within the register, necessary to build a url for it
        link (str): direct link to the entry
        organisation (Autor): Person or organisation in some function. e.g.:
            - authors of a statement,
            - expert at a hearing,
            - initiator of a Vorgang
            - authoring organisations of documents
    """

    betroffene_drucksachen: list[str]
    intention: str
    interne_id: str
    link: str
    organisation: Autor
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        betroffene_drucksachen = self.betroffene_drucksachen

        intention = self.intention

        interne_id = self.interne_id

        link = self.link

        organisation = self.organisation.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "betroffene_drucksachen": betroffene_drucksachen,
                "intention": intention,
                "interne_id": interne_id,
                "link": link,
                "organisation": organisation,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autor import Autor

        d = dict(src_dict)
        betroffene_drucksachen = cast(list[str], d.pop("betroffene_drucksachen"))

        intention = d.pop("intention")

        interne_id = d.pop("interne_id")

        link = d.pop("link")

        organisation = Autor.from_dict(d.pop("organisation"))

        lobbyregistereintrag = cls(
            betroffene_drucksachen=betroffene_drucksachen,
            intention=intention,
            interne_id=interne_id,
            link=link,
            organisation=organisation,
        )

        lobbyregistereintrag.additional_properties = d
        return lobbyregistereintrag

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
