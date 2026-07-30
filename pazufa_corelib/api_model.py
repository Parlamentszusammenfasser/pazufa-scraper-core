"""Pydantic models for the PaZuFa API.

Based on automatic generation and augmented with handcrafted additions.
"""

from __future__ import annotations

import warnings
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from pydantic import AnyHttpUrl, Field, RootModel, model_validator

from pazufa_corelib._api_model_hardening import (
    PaZuFaBaseModel,
    Sha256Hex,
    TzDatetime,
    check_meinung_scope,
)


class ApiKeyScope(StrEnum):
    """Permission level of an API key.
    """

    admin = "admin"
    collector = "collector"
    keyadder = "keyadder"


class ApiKeyStatus(PaZuFaBaseModel):
    expires_at: Annotated[
        TzDatetime,
        Field(
            description="When this key will expire. If `is_being_rotated` is true, this is the date the rotation is complete."
        ),
    ]
    is_being_rotated: Annotated[
        bool, Field(description="Whether this key is currently in a transition process")
    ]
    scope: ApiKeyScope


class RotationResponse(PaZuFaBaseModel):
    """Response body of POST /api/v2/auth/rotate.

    The spec declares this response inline rather than under
    `components/schemas`, so the generator does not emit a class for it. Fields
    mirror the inline schema exactly.
    """

    new_api_key: Annotated[
        str, Field(description="The newly created API key (shown only once)")
    ]
    rotation_complete_date: Annotated[
        TzDatetime,
        Field(description="Confirmed date when the old key will be invalidated"),
    ]


class AuthDeleteHeaderParams(PaZuFaBaseModel):
    api_key_delete: str


class Autor(PaZuFaBaseModel):
    fachgebiet: str | None = None
    lobbyregister: AnyHttpUrl | None = None     # replacing AnyUrl with AnyHttpUrl to make sure links are valid http links.
    organisation: str
    person: str | None = None


class CreateApiKey(PaZuFaBaseModel):
    expires_at: Annotated[
        TzDatetime | None, Field(description="The expiration date of the API Key")
    ] = None
    scope: ApiKeyScope


class Doktyp(StrEnum):
    eckpunktepapier = "eckpunktepapier"
    preparl_entwurf = "preparl-entwurf"
    entwurf = "entwurf"
    antrag = "antrag"
    anfrage = "anfrage"
    antwort = "antwort"
    mitteilung = "mitteilung"
    beschlussempf = "beschlussempf"
    stellungnahme = "stellungnahme"
    gutachten = "gutachten"
    redeprotokoll = "redeprotokoll"
    tops = "tops"
    tops_aend = "tops-aend"
    tops_ergz = "tops-ergz"
    gesetz = "gesetz"
    sonstig = "sonstig"


class DokumentFormat(StrEnum):
    ftm = "ftm"
    pazufa = "pazufa"


class EnumerationName(StrEnum):
    schlagworte = "schlagworte"
    stationstypen = "stationstypen"
    vorgangstypen = "vorgangstypen"
    parlamente = "parlamente"
    vgidtypen = "vgidtypen"
    dokumententypen = "dokumententypen"


class KeytagListing(PaZuFaBaseModel):
    dokumente: list[str] | None = None
    sitzungen: list[str] | None = None
    stationen: list[str] | None = None
    vorgaenge: list[str] | None = None


class Lobbyregistereintrag(PaZuFaBaseModel):
    betroffene_drucksachen: Annotated[
        list[str],
        Field(
            description="Array with associated Drucksachennummern.\nIs not crossreferenced in the database and just added as dataset"
        ),
    ]
    intention: Annotated[
        str,
        Field(description="Subject and reason for influencing the legislative process"),
    ]
    interne_id: Annotated[
        str,
        Field(
            description="Internal ID within the register, necessary to build a url for it"
        ),
    ]
    link: Annotated[AnyHttpUrl, Field(description="direct link to the entry")]
    organisation: Autor


class Mime(StrEnum):
    application_json = "application/json"
    application_pdf = "application/pdf"
    application_octet_stream = "application/octet-stream"
    text_plain = "text/plain"
    text_html = "text/html"


class Parlament(StrEnum):
    BT = "BT"
    BR = "BR"
    BV = "BV"
    EK = "EK"
    BB = "BB"
    BY = "BY"
    BE = "BE"
    HB = "HB"
    HH = "HH"
    HE = "HE"
    MV = "MV"
    NI = "NI"
    NW = "NW"
    RP = "RP"
    SL = "SL"
    SN = "SN"
    TH = "TH"
    SH = "SH"
    BW = "BW"
    ST = "ST"


class ReplacingEntry[T](PaZuFaBaseModel):
    """One replacement rule inside an admin PUT request.

    The generated mirror spells this out three times — once per payload type —
    and inlines a fresh copy of the payload model for each, under placeholder
    names the generator invents (`Value`, `Value1`, `Object`, `Object1`), even
    though those copies are field-for-field identical to `Autor` and `Gremium`.
    One generic replaces all six classes and lets the real models be reused.
    """

    replaced_by: Annotated[
        int,
        Field(
            description="This object is replaced by the object with index {} in the 'objects' list above. 0-Based indexing.",
            ge=0,
        ),
    ]
    values: list[T]


class Stationstyp(StrEnum):
    preparl_regent = "preparl-regent"
    preparl_eckpup = "preparl-eckpup"
    preparl_regbsl = "preparl-regbsl"
    preparl_vbegde = "preparl-vbegde"
    preparl_formvs = "preparl-formvs"
    parl_initiativ = "parl-initiativ"
    parl_antragsst = "parl-antragsst"
    parl_ausschber = "parl-ausschber"
    parl_vollvlsgn = "parl-vollvlsgn"
    parl_akzeptanz = "parl-akzeptanz"
    parl_ablehnung = "parl-ablehnung"
    parl_zurueckgz = "parl-zurueckgz"
    parl_ggentwurf = "parl-ggentwurf"
    parl_vermittas = "parl-vermittas"
    parl_verfgstop = "parl-verfgstop"
    postparl_vesja = "postparl-vesja"
    postparl_vesne = "postparl-vesne"
    postparl_gsblt = "postparl-gsblt"
    postparl_kraft = "postparl-kraft"
    sonstig = "sonstig"


class TouchedByEntry(PaZuFaBaseModel):
    key: Annotated[
        str | None, Field(description="Key hash of the scraper that touched the object")
    ] = None
    scraper_id: Annotated[
        UUID | None, Field(description="uuid of the scraper that touched this object")
    ] = None


class VgIdent(PaZuFaBaseModel):
    id: str
    typ: str


class Vorgangstyp(StrEnum):
    gg_einspruch = "gg-einspruch"
    gg_zustimmung = "gg-zustimmung"
    gg_land_parl = "gg-land-parl"
    gg_land_volk = "gg-land-volk"
    bw_einsatz = "bw-einsatz"
    sonstig = "sonstig"


class Dokument(PaZuFaBaseModel):
    api_id: Annotated[
        UUID | None,
        Field(
            description="optional, here for future references. Is generated by the server. If you set it use UUID version 5 with your collector id as namespace"
        ),
    ] = None
    autoren: Annotated[
        list[Autor],
        Field(
            description="List of authors of the document. Could be a person, organisation or a parliamentary body"
        ),
    ]
    drucksnr: str | None = None
    hash: Annotated[
        Sha256Hex,
        Field(
            description="corresponds to sha256+bytes, here for backwards compatibility"
        ),
    ]
    kurztitel: Annotated[
        str | None,
        Field(description="Brief, Summarized, layman-readable title of the document"),
    ] = None
    link: AnyHttpUrl
    meinung: Annotated[
        int | None,
        Field(
            description="General opinion of the gremium about the Document\nStellungnahme:       1=very bad, 5=very good\nBeschlussempfehlung: 1=rejection recommended, 2-4=accept in changed form, 5=acceptence recommended",
            ge=1,
            le=5,
        ),
    ] = None
    schlagworte: Annotated[
        list[str] | None, Field(description="Keywords associated with this document")
    ] = None
    titel: Annotated[str, Field(description="Official Title of the Document")]
    touched_by: Annotated[
        list[TouchedByEntry] | None,
        Field(
            description="list of scraper uuids / key database ids that have touched this object"
        ),
    ] = None
    typ: Doktyp
    volltext: Annotated[
        str, Field(description="Full text of the document, possibly normalized")
    ]
    vorwort: Annotated[
        str | None, Field(description="Preamble, synopsys or statement of intent")
    ] = None
    zp_erstellt: Annotated[
        TzDatetime | None,
        Field(
            description="Protocol of the session on 7.3., *created on 8.3.* modified on 9.3."
        ),
    ] = None
    zp_modifiziert: Annotated[
        TzDatetime,
        Field(
            description="Protocol of the session on 7.3., created on 8.3. *modified on 9.3*."
        ),
    ]
    zp_referenz: Annotated[
        TzDatetime,
        Field(
            description="Protocol of the *session on 7.3.*, created on 8.3. modified on 9.3."
        ),
    ]
    zusammenfassung: Annotated[
        str | None, Field(description="Summary of the document's contents")
    ] = None

    @model_validator(mode="after")
    def _check_meinung(self) -> Dokument:
        """Reject a ``meinung`` on document types where it carries no meaning.

        The rule itself lives in `_api_model_hardening` — it is domain knowledge
        the specification does not express, and keeping it out of a regenerable
        file is the point. Only the hook belongs here.
        """
        check_meinung_scope(self.meinung, self.typ)
        return self


class DokumentOrApiId(RootModel[Dokument | UUID]):
    root: Dokument | UUID


class Gremium(PaZuFaBaseModel):
    link: AnyHttpUrl | None = None
    name: Annotated[
        str,
        Field(
            description="Name of the body. 'plenum', 'regierung', 'volk' are reserved"
        ),
    ]
    parlament: Parlament
    wahlperiode: Annotated[int, Field(ge=0)]


class Station(PaZuFaBaseModel):
    additional_links: Annotated[
        list[AnyHttpUrl] | None,
        Field(
            description="Further links to interesting infos for this station",
            examples=["https://example.com/video/of/plenary/session"],
        ),
    ] = None
    api_id: Annotated[
        UUID | None,
        Field(
            description="optional, here for future references. Is generated by the server. If you set it use UUID version 5 with your collector id as namespace"
        ),
    ] = None
    dokumente: Annotated[
        list[DokumentOrApiId],
        Field(
            description="Documents that make up the Station or are associated with it.\nNOTE: At upload time, only complete documents are accepted;\nAt download time, only the API IDs of the documents are passed down to the clients."
        ),
    ]
    gremium: Gremium
    gremium_federf: Annotated[
        bool | None,
        Field(
            description="If the station if of type parl-ausschbsl, this field should be set if the committee is the main committee ('federführend')"
        ),
    ] = None
    link: Annotated[
        AnyHttpUrl | None,
        Field(
            description="Link to a web page describing this station in more detail, NOT to a pdf document"
        ),
    ] = None
    schlagworte: list[str] | None = None
    stellungnahmen: list[DokumentOrApiId] | None = None
    titel: Annotated[
        str | None,
        Field(
            description="optional title, if other data does not provide a proper description"
        ),
    ] = None
    touched_by: Annotated[
        list[TouchedByEntry] | None,
        Field(
            description="list of scraper uuids / key database ids that have touched this object"
        ),
    ] = None
    typ: Stationstyp
    zp_modifiziert: Annotated[
        TzDatetime | None,
        Field(
            description="Date of the last relevant action within this station. i.e.: last session of a committee"
        ),
    ] = None
    zp_start: Annotated[
        TzDatetime,
        Field(
            description="Date of the first action within this station. i.e.: First session of a committee"
        ),
    ]


class Top(PaZuFaBaseModel):
    dokumente: Annotated[
        list[DokumentOrApiId] | None,
        Field(description="documents handled in this agenda item"),
    ] = None
    nummer: Annotated[int, Field(description="number of this item on the agenda", ge=0)]
    titel: str
    vorgang_id: Annotated[
        list[UUID] | None,
        Field(
            description="api ids of associated Vorgang objects.\nIs ignored at upload time, but passed at download time.\nThe matching happens via the documents supplied below"
        ),
    ] = None


class Vorgang(PaZuFaBaseModel):
    api_id: Annotated[
        UUID,
        Field(description="Use UUID version 5 with your collector id as namespace"),
    ]
    ids: list[VgIdent] | None = None
    initiatoren: Annotated[
        list[Autor],
        Field(
            description="List of persons or organisations, which initiated the Vorgang."
        ),
    ]
    kurztitel: str | None = None
    links: list[AnyHttpUrl] | None = None
    lobbyregister: list[Lobbyregistereintrag] | None = None
    stationen: list[Station]
    titel: str
    touched_by: Annotated[
        list[TouchedByEntry] | None,
        Field(
            description="list of scraper uuids / key database ids that have touched this object"
        ),
    ] = None
    typ: Vorgangstyp
    verfassungsaendernd: Annotated[
        bool,
        Field(
            description="Is this Vorgang directly intended to change the constitution of whatever state it happens\nin?"
        ),
    ]
    wahlperiode: Annotated[
        int, Field(description="number of the electoral period", ge=0)
    ]


class Sitzung(PaZuFaBaseModel):
    api_id: Annotated[
        UUID | None,
        Field(
            description="optional, here for future references. Is generated by the server.\nIf you set it use UUID version 5 with your collector id as namespace"
        ),
    ] = None
    dokumente: Annotated[
        list[DokumentOrApiId] | None,
        Field(description="Announcements, agendas and changed/amended agendas"),
    ] = None
    experten: Annotated[
        list[Autor] | None,
        Field(
            description="List of invited experts. if this is not null or empty, a session is a hearing."
        ),
    ] = None
    gremium: Gremium
    link: AnyHttpUrl | None = None
    nummer: Annotated[int, Field(ge=0)]
    public: bool
    termin: TzDatetime
    titel: Annotated[str | None, Field(description="Title if applicable")] = None
    tops: list[Top]
    touched_by: Annotated[
        list[TouchedByEntry] | None,
        Field(
            description="list of scraper uuids / key database ids that have touched this object"
        ),
    ] = None


# ---------------------------------------------------------------------------
# Admin PUT request bodies
# ---------------------------------------------------------------------------


class AutorenPutRequest(PaZuFaBaseModel):
    """Request body for PUT /api/v2/autoren."""

    objects: list[Autor]
    replacing: list[ReplacingEntry[Autor]] | None = None


class GremienPutRequest(PaZuFaBaseModel):
    """Request body for PUT /api/v2/gremien."""

    objects: list[Gremium]
    replacing: list[ReplacingEntry[Gremium]] | None = None


class EnumerationPutRequest(PaZuFaBaseModel):
    """Request body for PUT /api/v2/enumeration/{name}."""

    objects: list[str]
    replacing: list[ReplacingEntry[str]] | None = None


# ---------------------------------------------------------------------------
# Deprecated aliases
# ---------------------------------------------------------------------------

_RENAMED: dict[str, str] = {
    "Scope": "ApiKeyScope",
    "TouchedByItem": "TouchedByEntry",
    "EnumerationNames": "EnumerationName",
    "Lobbyregeintrag": "Lobbyregistereintrag",
}


def __getattr__(name: str) -> Any:
    """Serve the pre-rename class names, with a ``DeprecationWarning``.

    Returns the *same* class object rather than a subclass, so ``isinstance``
    checks, pydantic field annotations and unions keep working unchanged for
    anyone still on the old name.

    Unknown names must still raise ``AttributeError`` — Python probes modules
    for attributes such as ``__path__`` and ``__all__``, and swallowing those
    lookups breaks imports in ways that are hard to trace.
    """
    new = _RENAMED.get(name)
    if new is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    warnings.warn(
        f"{name!r} was renamed to {new!r} and will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    return globals()[new]


if TYPE_CHECKING:
    # Seen only by the type checker. Without this block a module-level
    # __getattr__ makes mypy accept *any* attribute, so the old names would pass
    # silently. Needs `enable_error_code = ["deprecated"]`, which is set in
    # pyproject.toml.
    from typing_extensions import deprecated

    @deprecated("renamed to TouchedByEntry")
    class TouchedByItem(TouchedByEntry): ...

    @deprecated("renamed to Lobbyregistereintrag")
    class Lobbyregeintrag(Lobbyregistereintrag): ...

    # Enums cannot be subclassed once they have members, so these two get a
    # plain alias: mypy resolves the type correctly, but only the runtime
    # warning above flags them as deprecated.
    Scope = ApiKeyScope
    EnumerationNames = EnumerationName
