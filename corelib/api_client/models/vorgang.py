from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.vorgangstyp import Vorgangstyp
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autor import Autor
    from ..models.lobbyregeintrag import Lobbyregeintrag
    from ..models.station import Station
    from ..models.touched_by_item import TouchedByItem
    from ..models.vg_ident import VgIdent


T = TypeVar("T", bound="Vorgang")


@_attrs_define
class Vorgang:
    """'Master-Objekt' der API. Der Wrapper um Stationen, die den Beratungsverlauf tatsächlich beschreiben. Ein Vorgang
    kann dabei nicht nur ein Gesetz, sondern auch ein parlamentarischer Antrag sein.

        Example:
            {'api_id': '123e4567-e89b-12d3-a456-426614174000', 'ids': [{'id': '20/12345', 'typ': 'initdrucks'}, {'id':
                'WR-2024-01', 'typ': 'vorgnr'}], 'initiatoren': [{'fachgebiet': 'Innenpolitik', 'organisation': 'CDU/CSU-
                Fraktion', 'person': 'Dr. Friedrich Merz'}, {'organisation': 'SPD-Fraktion'}], 'kurztitel': 'Wahlrechtsreform',
                'links': ['https://www.bundestag.de/dokumente/textarchiv/2024/wahlrechtsreform',
                'https://dip.bundestag.de/vorgang/123456'], 'lobbyregister': [{'betroffene_drucksachen': ['BT-Drs. 20/12345'],
                'intention': 'Stellungnahme zu Auswirkungen der Gesetzesänderung auf die deutsche Wirtschaft.', 'interne_id':
                'LR-ID-12345678', 'link': 'https://www.lobbyregister.bundestag.de/eintragung/12345678', 'organisation':
                {'organisation': 'Bundesverband der Deutschen Industrie e.V.', 'person': 'Dr. Johannes Weber'}}], 'stationen':
                [{'api_id': 'f1e2d3c4-b5a6-7890-abcd-1234567890cd', 'dokumente': [], 'parlament': 'BT', 'titel': 'Erste Lesung
                im Bundestag', 'typ': 'parl-vollvlsgn', 'zp_modifiziert': '2024-04-15T13:45:00+02:00', 'zp_start':
                '2024-04-15T10:00:00+02:00'}], 'titel': 'Gesetz zur Änderung des Bundeswahlgesetzes und anderer Gesetze', 'typ':
                'gg-einspruch', 'verfassungsaendernd': False, 'wahlperiode': 20}

        Attributes:
            api_id (UUID):  Example: 123e4567-e89b-12d3-a456-426614174000.
            initiatoren (list[Autor]): Liste von Personen oder Organisationen, die den Vorgang initiiert haben. Kann z.B.
                eine Person, eine Organisation oder ein Gremium sein.
            stationen (list[Station]):
            titel (str):
            typ (Vorgangstyp): Der Gesetzgebungstrack auf dem wir uns befinden. Zum Beispiel: gesetzgebung -
                Einspruchsgesetz. Legt fest, welche Stationen im Vorgang möglich sind zusammen mit den Parlamenten in den
                Stationen
            verfassungsaendernd (bool):
            wahlperiode (int): Nummer der Wahlperiode, in der der Vorgang stattfindet
            ids (list[VgIdent] | Unset):
            kurztitel (str | Unset):
            links (list[str] | Unset):
            lobbyregister (list[Lobbyregeintrag] | Unset):
            touched_by (list[TouchedByItem] | Unset): list of scraper uuids / key database ids that have touched this object
    """

    api_id: UUID
    initiatoren: list[Autor]
    stationen: list[Station]
    titel: str
    typ: Vorgangstyp
    verfassungsaendernd: bool
    wahlperiode: int
    ids: list[VgIdent] | Unset = UNSET
    kurztitel: str | Unset = UNSET
    links: list[str] | Unset = UNSET
    lobbyregister: list[Lobbyregeintrag] | Unset = UNSET
    touched_by: list[TouchedByItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        api_id = str(self.api_id)

        initiatoren = []
        for initiatoren_item_data in self.initiatoren:
            initiatoren_item = initiatoren_item_data.to_dict()
            initiatoren.append(initiatoren_item)

        stationen = []
        for stationen_item_data in self.stationen:
            stationen_item = stationen_item_data.to_dict()
            stationen.append(stationen_item)

        titel = self.titel

        typ = self.typ.value

        verfassungsaendernd = self.verfassungsaendernd

        wahlperiode = self.wahlperiode

        ids: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.ids, Unset):
            ids = []
            for ids_item_data in self.ids:
                ids_item = ids_item_data.to_dict()
                ids.append(ids_item)

        kurztitel = self.kurztitel

        links: list[str] | Unset = UNSET
        if not isinstance(self.links, Unset):
            links = self.links

        lobbyregister: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.lobbyregister, Unset):
            lobbyregister = []
            for lobbyregister_item_data in self.lobbyregister:
                lobbyregister_item = lobbyregister_item_data.to_dict()
                lobbyregister.append(lobbyregister_item)

        touched_by: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.touched_by, Unset):
            touched_by = []
            for componentsschemastouched_by_item_data in self.touched_by:
                componentsschemastouched_by_item = componentsschemastouched_by_item_data.to_dict()
                touched_by.append(componentsschemastouched_by_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "api_id": api_id,
                "initiatoren": initiatoren,
                "stationen": stationen,
                "titel": titel,
                "typ": typ,
                "verfassungsaendernd": verfassungsaendernd,
                "wahlperiode": wahlperiode,
            }
        )
        if ids is not UNSET:
            field_dict["ids"] = ids
        if kurztitel is not UNSET:
            field_dict["kurztitel"] = kurztitel
        if links is not UNSET:
            field_dict["links"] = links
        if lobbyregister is not UNSET:
            field_dict["lobbyregister"] = lobbyregister
        if touched_by is not UNSET:
            field_dict["touched_by"] = touched_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autor import Autor
        from ..models.lobbyregeintrag import Lobbyregeintrag
        from ..models.station import Station
        from ..models.touched_by_item import TouchedByItem
        from ..models.vg_ident import VgIdent

        d = dict(src_dict)
        api_id = UUID(d.pop("api_id"))

        initiatoren = []
        _initiatoren = d.pop("initiatoren")
        for initiatoren_item_data in _initiatoren:
            initiatoren_item = Autor.from_dict(initiatoren_item_data)

            initiatoren.append(initiatoren_item)

        stationen = []
        _stationen = d.pop("stationen")
        for stationen_item_data in _stationen:
            stationen_item = Station.from_dict(stationen_item_data)

            stationen.append(stationen_item)

        titel = d.pop("titel")

        typ = Vorgangstyp(d.pop("typ"))

        verfassungsaendernd = d.pop("verfassungsaendernd")

        wahlperiode = d.pop("wahlperiode")

        _ids = d.pop("ids", UNSET)
        ids: list[VgIdent] | Unset = UNSET
        if _ids is not UNSET:
            ids = []
            for ids_item_data in _ids:
                ids_item = VgIdent.from_dict(ids_item_data)

                ids.append(ids_item)

        kurztitel = d.pop("kurztitel", UNSET)

        links = cast(list[str], d.pop("links", UNSET))

        _lobbyregister = d.pop("lobbyregister", UNSET)
        lobbyregister: list[Lobbyregeintrag] | Unset = UNSET
        if _lobbyregister is not UNSET:
            lobbyregister = []
            for lobbyregister_item_data in _lobbyregister:
                lobbyregister_item = Lobbyregeintrag.from_dict(lobbyregister_item_data)

                lobbyregister.append(lobbyregister_item)

        _touched_by = d.pop("touched_by", UNSET)
        touched_by: list[TouchedByItem] | Unset = UNSET
        if _touched_by is not UNSET:
            touched_by = []
            for componentsschemastouched_by_item_data in _touched_by:
                componentsschemastouched_by_item = TouchedByItem.from_dict(componentsschemastouched_by_item_data)

                touched_by.append(componentsschemastouched_by_item)

        vorgang = cls(
            api_id=api_id,
            initiatoren=initiatoren,
            stationen=stationen,
            titel=titel,
            typ=typ,
            verfassungsaendernd=verfassungsaendernd,
            wahlperiode=wahlperiode,
            ids=ids,
            kurztitel=kurztitel,
            links=links,
            lobbyregister=lobbyregister,
            touched_by=touched_by,
        )

        vorgang.additional_properties = d
        return vorgang

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
