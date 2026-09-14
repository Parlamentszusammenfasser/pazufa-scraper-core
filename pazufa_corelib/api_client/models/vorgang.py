from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.ressort import Ressort
from ..models.sachgebiet import Sachgebiet
from ..models.vorgangstyp import Vorgangstyp
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autor import Autor
    from ..models.lobbyregistereintrag import Lobbyregistereintrag
    from ..models.station import Station
    from ..models.touched_by_inner import TouchedByInner
    from ..models.vg_ident import VgIdent


T = TypeVar("T", bound="Vorgang")


@_attrs_define
class Vorgang:
    """'Master Object of the API. Wrapper type around stations.
    `Vorgang` describes not only legislative processes, but also other kinds of parliamentary
    proceedings

        Attributes:
            api_id (UUID): Use UUID version 5 with your collector id as namespace
            initiatoren (list[Autor]): List of persons or organisations, which initiated the Vorgang.
            stationen (list[Station]): List of stations, the core of what happens in one Proceeding
            titel (str):
            typ (Vorgangstyp): The legislative Track we are on. Together with a parliament, this tells us about the possible
                stations that can occurr within
            verfassungsaendernd (bool): Is this Vorgang directly intended to change the constitution of whatever state it
                happens
                in?
            wahlperiode (int): number of the electoral period
            ids (list[VgIdent] | Unset):
            kurztitel (None | str | Unset):
            links (list[str] | Unset):
            lobbyregister (list[Lobbyregistereintrag] | Unset): Lobby register annotations from Bundestag sources
            ressort (None | Ressort | Unset):
            sachgebiete (list[Sachgebiet] | Unset): Sachgebiet information
            schlagworte (list[str] | Unset): General Vorgangs-Schlagworte
            touched_by (list[TouchedByInner] | Unset): list of scraper uuids / key database ids that have touched this
                object
    """

    api_id: UUID
    initiatoren: list[Autor]
    stationen: list[Station]
    titel: str
    typ: Vorgangstyp
    verfassungsaendernd: bool
    wahlperiode: int
    ids: list[VgIdent] | Unset = UNSET
    kurztitel: None | str | Unset = UNSET
    links: list[str] | Unset = UNSET
    lobbyregister: list[Lobbyregistereintrag] | Unset = UNSET
    ressort: None | Ressort | Unset = UNSET
    sachgebiete: list[Sachgebiet] | Unset = UNSET
    schlagworte: list[str] | Unset = UNSET
    touched_by: list[TouchedByInner] | Unset = UNSET
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

        kurztitel: None | str | Unset
        if isinstance(self.kurztitel, Unset):
            kurztitel = UNSET
        else:
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

        ressort: None | str | Unset
        if isinstance(self.ressort, Unset):
            ressort = UNSET
        elif isinstance(self.ressort, Ressort):
            ressort = self.ressort.value
        else:
            ressort = self.ressort

        sachgebiete: list[int] | Unset = UNSET
        if not isinstance(self.sachgebiete, Unset):
            sachgebiete = []
            for sachgebiete_item_data in self.sachgebiete:
                sachgebiete_item = sachgebiete_item_data.value
                sachgebiete.append(sachgebiete_item)

        schlagworte: list[str] | Unset = UNSET
        if not isinstance(self.schlagworte, Unset):
            schlagworte = self.schlagworte

        touched_by: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.touched_by, Unset):
            touched_by = []
            for touched_by_item_data in self.touched_by:
                touched_by_item = touched_by_item_data.to_dict()
                touched_by.append(touched_by_item)

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
        if ressort is not UNSET:
            field_dict["ressort"] = ressort
        if sachgebiete is not UNSET:
            field_dict["sachgebiete"] = sachgebiete
        if schlagworte is not UNSET:
            field_dict["schlagworte"] = schlagworte
        if touched_by is not UNSET:
            field_dict["touched_by"] = touched_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.autor import Autor
        from ..models.lobbyregistereintrag import Lobbyregistereintrag
        from ..models.station import Station
        from ..models.touched_by_inner import TouchedByInner
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

        def _parse_kurztitel(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        kurztitel = _parse_kurztitel(d.pop("kurztitel", UNSET))

        links = cast(list[str], d.pop("links", UNSET))

        _lobbyregister = d.pop("lobbyregister", UNSET)
        lobbyregister: list[Lobbyregistereintrag] | Unset = UNSET
        if _lobbyregister is not UNSET:
            lobbyregister = []
            for lobbyregister_item_data in _lobbyregister:
                lobbyregister_item = Lobbyregistereintrag.from_dict(lobbyregister_item_data)

                lobbyregister.append(lobbyregister_item)

        def _parse_ressort(data: object) -> None | Ressort | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                ressort_type_1 = Ressort(data)

                return ressort_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Ressort | Unset, data)

        ressort = _parse_ressort(d.pop("ressort", UNSET))

        _sachgebiete = d.pop("sachgebiete", UNSET)
        sachgebiete: list[Sachgebiet] | Unset = UNSET
        if _sachgebiete is not UNSET:
            sachgebiete = []
            for sachgebiete_item_data in _sachgebiete:
                sachgebiete_item = Sachgebiet(sachgebiete_item_data)

                sachgebiete.append(sachgebiete_item)

        schlagworte = cast(list[str], d.pop("schlagworte", UNSET))

        _touched_by = d.pop("touched_by", UNSET)
        touched_by: list[TouchedByInner] | Unset = UNSET
        if _touched_by is not UNSET:
            touched_by = []
            for touched_by_item_data in _touched_by:
                touched_by_item = TouchedByInner.from_dict(touched_by_item_data)

                touched_by.append(touched_by_item)

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
            ressort=ressort,
            sachgebiete=sachgebiete,
            schlagworte=schlagworte,
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
