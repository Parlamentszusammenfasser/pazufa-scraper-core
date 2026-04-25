from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.autor import Autor


T = TypeVar("T", bound="Lobbyregeintrag")


@_attrs_define
class Lobbyregeintrag:
    """Eintrag im Bundestagslobbyregister zu einem bestimmten Vorgang

    Example:
        {'betroffene_drucksachen': ['BT-Drs. 20/12345', 'BT-Drs. 20/12346'], 'intention': 'Stellungnahme zu Auswirkungen
            der Gesetzesänderung auf die deutsche Wirtschaft und Vorschläge zur Anpassung in § 15 des Gesetzesentwurfs.',
            'interne_id': 'LR-ID-12345678', 'link': 'https://www.lobbyregister.bundestag.de/eintragung/12345678',
            'organisation': {'lobbyregister': 'https://www.lobbyregister.bundestag.de/suche/experte/12345', 'organisation':
            'Bundesverband der Deutschen Industrie e.V.'}}

    Attributes:
        betroffene_drucksachen (list[str]): Stringarray mit betroffenen Drucksachennummern. Wird in der Datenbank
            _nicht_ integriert und nur flach aufgelegt
        intention (str): Lobbyregistereintrag zu dem  Was und Warum man auf den Vorgang Einfluss nehmen will
        interne_id (str): Interne ID des Lobbyregisters, notwendig für die bildung von Links
        link (str): Direktlink zum Lobbyregistereintrag
        organisation (Autor): Eine Person oder Organisation, die eine bestimmte Funktion übernommen hat. Z.B: Autor
            einer Stellungnahme, Experte bei einer Anhörung, Initiator eines Vorgangs. Example: {'fachgebiet':
            'Verfassungsrecht', 'lobbyregister': 'https://www.lobbyregister.bundestag.de/suche/experte/12345',
            'organisation': 'Universität Heidelberg', 'person': 'Prof. Dr. Susanne Meyer'}.
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

        lobbyregeintrag = cls(
            betroffene_drucksachen=betroffene_drucksachen,
            intention=intention,
            interne_id=interne_id,
            link=link,
            organisation=organisation,
        )

        lobbyregeintrag.additional_properties = d
        return lobbyregeintrag

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
