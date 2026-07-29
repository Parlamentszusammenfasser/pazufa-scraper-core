"""
Pydantic models for the PaZuFa API.

Based on automatic generation and augmented with handcrafted additions.
"""


from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import AnyUrl, AwareDatetime, BaseModel, Field, RootModel

from pazufa_corelib._api_model_hardening import (
    HttpUrlStr,
    TzDatetime,
    check_meinung_scope,
)


class KeyTag(RootModel[str]):
    root: Annotated[
        str,
        Field(
            description="A uniquely identifying string that is generated from key data within the database"
        ),
    ]


class EnumerationNames(StrEnum):
    schlagworte = "schlagworte"
    stationstypen = "stationstypen"
    vorgangstypen = "vorgangstypen"
    parlamente = "parlamente"
    vgidtypen = "vgidtypen"
    dokumententypen = "dokumententypen"


class Scope(StrEnum):
    admin = "admin"
    collector = "collector"
    keyadder = "keyadder"


class CreateApiKey(BaseModel):
    scope: Scope
    expires_at: Annotated[
        AwareDatetime | None,
        Field(
            description="The expiration date of the API Key",
            examples=["2024-12-31T23:59:59+00:00"],
        ),
    ] = None


class RotationResponse(BaseModel):
    new_api_key: Annotated[
        str, Field(description="The newly created API key (shown only once)")
    ]
    rotation_complete_date: Annotated[
        AwareDatetime,
        Field(description="Confirmed date when the old key will be invalidated"),
    ]


class ApiKeyStatus(BaseModel):
    scope: Scope
    expires_at: Annotated[
        AwareDatetime,
        Field(
            description="When this key will expire. If is_being_rotated is true, this is the date the rotation is complete."
        ),
    ]
    is_being_rotated: Annotated[
        bool, Field(description="Whether this key is currently in a transition process")
    ]


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


class Vorgangstyp(StrEnum):
    gg_einspruch = "gg-einspruch"
    gg_zustimmung = "gg-zustimmung"
    int_vertrag_zustimmung = "int-vertrag-zustimmung"
    int_vertrag_einspruch = "int-vertrag-einspruch"
    gg_land_parl = "gg-land-parl"
    gg_land_volk = "gg-land-volk"
    bw_einsatz = "bw-einsatz"
    sonstig = "sonstig"


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
    parl_verfgstop = "parl-verfgstop"
    parl_zurueckgz = "parl-zurueckgz"
    parl_ggentwurf = "parl-ggentwurf"
    parl_vermittas = "parl-vermittas"
    postparl_vesja = "postparl-vesja"
    postparl_vesne = "postparl-vesne"
    postparl_gsblt = "postparl-gsblt"
    postparl_kraft = "postparl-kraft"
    sonstig = "sonstig"


class VgIdentTyp(RootModel[str]):
    root: Annotated[
        str,
        Field(
            description="Type of an identifyer of a Vorgang. Can contain whatever a parliament uses to identify any complete process. Currently in existence: vorgnr, api-id, initdrucks, sonstig. If possible, please do not invent any type like `inids`, and use the ones in existence",
            examples=["initdrucks"],
        ),
    ]


class Doktyp(StrEnum):
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


class Gremium(BaseModel):
    parlament: Parlament
    wahlperiode: Annotated[int, Field(ge=0)]
    link: AnyUrl | None = None
    name: Annotated[
        str,
        Field(
            description="Name of the body. 'plenum', 'regierung', 'volk' are reserved",
            examples=["Ausschuss für Inneres und Gemüseauflauf"],
        ),
    ]


class TouchedByItem(BaseModel):
    scraper_id: Annotated[
        UUID | None, Field(description="uuid of the scraper that touched this object")
    ] = None
    key: Annotated[
        str | None, Field(description="Key hash of the scraper that touched the object")
    ] = None


class TouchedBy(RootModel[list[TouchedByItem]]):
    root: Annotated[
        list[TouchedByItem],
        Field(
            description="list of scraper uuids / key database ids that have touched this object"
        ),
    ]


class Strategy(StrEnum):
    sha256_bytes = "sha256+bytes"
    sha256_text = "sha256+text"
    sha1_bytes = "sha1+bytes"


class VgIdent(BaseModel):
    id: Annotated[str, Field(examples=["123e4567-e"])]
    typ: VgIdentTyp


class Autor(BaseModel):
    person: str | None = None
    organisation: str
    fachgebiet: str | None = None
    lobbyregister: AnyUrl | None = None


class Sachgebiet(IntEnum):
    integer_1000 = 1000
    integer_1010 = 1010
    integer_1030 = 1030
    integer_1050 = 1050
    integer_1060 = 1060
    integer_1070 = 1070
    integer_1080 = 1080
    integer_1100 = 1100
    integer_1110 = 1110
    integer_1200 = 1200
    integer_1210 = 1210
    integer_1220 = 1220
    integer_1230 = 1230
    integer_1240 = 1240
    integer_1300 = 1300
    integer_1310 = 1310
    integer_1320 = 1320
    integer_1330 = 1330
    integer_1340 = 1340
    integer_1350 = 1350
    integer_1400 = 1400
    integer_1410 = 1410
    integer_1420 = 1420
    integer_1430 = 1430
    integer_1500 = 1500
    integer_1510 = 1510
    integer_1520 = 1520
    integer_1530 = 1530
    integer_1540 = 1540
    integer_1600 = 1600
    integer_1610 = 1610
    integer_1620 = 1620
    integer_2000 = 2000
    integer_2010 = 2010
    integer_2020 = 2020
    integer_2030 = 2030
    integer_2040 = 2040
    integer_2050 = 2050
    integer_2060 = 2060
    integer_2070 = 2070
    integer_2080 = 2080
    integer_2090 = 2090
    integer_2100 = 2100
    integer_2110 = 2110
    integer_2120 = 2120
    integer_2130 = 2130
    integer_2200 = 2200
    integer_2300 = 2300
    integer_2400 = 2400
    integer_2410 = 2410
    integer_2420 = 2420
    integer_2430 = 2430
    integer_2440 = 2440
    integer_2450 = 2450
    integer_2500 = 2500
    integer_2510 = 2510
    integer_2520 = 2520
    integer_2530 = 2530
    integer_2600 = 2600
    integer_2610 = 2610
    integer_2620 = 2620
    integer_2630 = 2630
    integer_2640 = 2640
    integer_2650 = 2650
    integer_2660 = 2660
    integer_2700 = 2700
    integer_2800 = 2800
    integer_2810 = 2810
    integer_2820 = 2820
    integer_2830 = 2830
    integer_2840 = 2840
    integer_3100 = 3100
    integer_3110 = 3110
    integer_3120 = 3120
    integer_3130 = 3130
    integer_3140 = 3140
    integer_3200 = 3200
    integer_3300 = 3300
    integer_3310 = 3310
    integer_3320 = 3320
    integer_3330 = 3330
    integer_3400 = 3400
    integer_4100 = 4100
    integer_4200 = 4200
    integer_4210 = 4210
    integer_4220 = 4220
    integer_4230 = 4230
    integer_4240 = 4240
    integer_4250 = 4250
    integer_4260 = 4260
    integer_4300 = 4300
    integer_4310 = 4310
    integer_4320 = 4320
    integer_4330 = 4330
    integer_4400 = 4400
    integer_4500 = 4500
    integer_5000 = 5000
    integer_5010 = 5010
    integer_5020 = 5020
    integer_5030 = 5030
    integer_5040 = 5040
    integer_5050 = 5050
    integer_5060 = 5060
    integer_5070 = 5070
    integer_5080 = 5080
    integer_5100 = 5100
    integer_5110 = 5110
    integer_5120 = 5120
    integer_5130 = 5130
    integer_5140 = 5140
    integer_5150 = 5150
    integer_5200 = 5200
    integer_5210 = 5210
    integer_5220 = 5220
    integer_5230 = 5230
    integer_5240 = 5240
    integer_5250 = 5250
    integer_5260 = 5260
    integer_5270 = 5270
    integer_6100 = 6100
    integer_6110 = 6110
    integer_6120 = 6120
    integer_6130 = 6130
    integer_6140 = 6140
    integer_6150 = 6150
    integer_6160 = 6160
    integer_6200 = 6200
    integer_6300 = 6300
    integer_6400 = 6400
    integer_6410 = 6410
    integer_6500 = 6500
    integer_6510 = 6510
    integer_6520 = 6520
    integer_6530 = 6530
    integer_6600 = 6600
    integer_6700 = 6700
    integer_6800 = 6800
    integer_6900 = 6900
    integer_7100 = 7100
    integer_7200 = 7200
    integer_7300 = 7300
    integer_7400 = 7400
    integer_7500 = 7500
    integer_7600 = 7600
    integer_7700 = 7700
    integer_7710 = 7710
    integer_7720 = 7720
    integer_7730 = 7730
    integer_7740 = 7740
    integer_7750 = 7750
    integer_7800 = 7800
    integer_8100 = 8100
    integer_8200 = 8200
    integer_8300 = 8300
    integer_8310 = 8310
    integer_8320 = 8320
    integer_8330 = 8330
    integer_8340 = 8340
    integer_8350 = 8350
    integer_8400 = 8400
    integer_8600 = 8600
    integer_8700 = 8700
    integer_8800 = 8800
    integer_9900 = 9900
    integer_9999 = 9999


class Mime(StrEnum):
    application_json = "application/json"
    application_pdf = "application/pdf"
    text_plain = "text/plain"
    text_html = "text/html"


class Zusammenfassungstupel(BaseModel):
    typ: Annotated[
        str | None,
        Field(
            description="Type of summary, if the summary is made up of parts",
            examples=["Basisinformationen"],
        ),
    ] = None
    inhalt: Annotated[
        str | None,
        Field(
            description="Content of the Summary part",
            examples=[
                "Das Gesetz zur Haarfärbeverordnung dient der Umsetzung der EU-Richtline 42/69420 zur Schuppenfreiheit bei Eigenschaftsänderlichen Haarmodifikationen vor..."
            ],
        ),
    ] = None


class Ressort(StrEnum):
    Arbeit = "Arbeit"
    Bildung = "Bildung"
    Digitalisierung = "Digitalisierung"
    Energie = "Energie"
    Ernährung = "Ernährung"
    Europa = "Europa"
    Familie_Senioren = "Familie/Senioren"
    Finanzen = "Finanzen"
    Forschung = "Forschung"
    Forsten = "Forsten"
    Frauen_Gleichstellung = "Frauen/Gleichstellung"
    Gesundheit_Pflege_Prävention = "Gesundheit/Pflege/Prävention"
    Heimat = "Heimat"
    Inneres = "Inneres"
    Integration_Migration = "Integration/Migration"
    Jugend = "Jugend"
    Justiz = "Justiz"
    Kinder = "Kinder"
    Klimaschutz = "Klimaschutz"
    Kommunales = "Kommunales"
    Kunst_Kultur = "Kunst/Kultur"
    Landes__Stadtentwicklung = "Landes-/Stadtentwicklung"
    Ländlicher_Raum = "Ländlicher Raum"
    Landwirtschaft = "Landwirtschaft"
    Soziales = "Soziales"
    Sport = "Sport"
    Tourismus = "Tourismus"
    Umwelt = "Umwelt"
    Verbraucherschutz = "Verbraucherschutz"
    Verkehr_Infrastruktur = "Verkehr/Infrastruktur"
    Wirtschaft = "Wirtschaft"
    Wissenschaft = "Wissenschaft"
    Wohnen_Bau = "Wohnen/Bau"


class HashItem(BaseModel):
    value: Annotated[
        str,
        Field(
            description="Hash value as string of hexadecimal octets",
            max_length=64,
            min_length=40,
        ),
    ]
    strategy: Annotated[
        Strategy,
        Field(
            description="The Strategy used to compute the hash. sha256+text denotes that not the raw file, but the _exact_ volltext field of the document was hashed. All text must be utf-8, remain stable under subsequent extraction, and mime must be set to text/plain."
        ),
    ]
    mime: Mime


class Dokument(BaseModel):
    api_id: Annotated[
        UUID | None,
        Field(
            description="optional, here for future references. Is generated by the server. If you set it use UUID version 5 with your collector id as namespace"
        ),
    ] = None
    touched_by: TouchedBy | None = None
    drucksnr: str | None = None
    typ: Doktyp
    titel: Annotated[str, Field(description="Offizieller Titel")]
    kurztitel: Annotated[
        str | None,
        Field(description="Brief, Summarized, layman-readable title of the document"),
    ] = None
    vorwort: Annotated[
        str | None, Field(description="Preabmle, synopsys or statement of intent")
    ] = None
    volltext: Annotated[
        str, Field(description="Full text of the document, possibly normalized")
    ]
    zusammenfassung: str | list[Zusammenfassungstupel] | None = None
    zp_modifiziert: Annotated[
        AwareDatetime,
        Field(
            description="Protocol of the session on 7.3., created on 8.3. modified on 9.3.",
            examples=["2024-03-09T00:00:00+00:00"],
        ),
    ]
    zp_referenz: Annotated[
        AwareDatetime,
        Field(
            description="Protocol of the session on 7.3., created on 8.3. modified on 9.3.",
            examples=["2024-03-07T00:00:00+00:00"],
        ),
    ]
    zp_erstellt: Annotated[
        AwareDatetime | None,
        Field(
            description="Protocol of the session on 7.3., created on 8.3. modified on 9.3.",
            examples=["2024-03-08T00:00:00+00:00"],
        ),
    ] = None
    link: AnyUrl
    hash: str | list[HashItem]
    subdoc_id: Annotated[
        int | None,
        Field(
            description="If a document contains more than one semantically closed document (x opinions in a collected file for example) this denotes the index of the sub-file in question. They can potentially share a hash.",
            ge=0,
        ),
    ] = None
    meinung: Annotated[
        int | None,
        Field(
            description="General opinion of the station in question. 1=very bad, 5=very good OR 1=rejection recommended, 2-4=accept in changed form, 5=acceptence recommended",
            ge=1,
            le=5,
        ),
    ] = None
    schlagworte: list[str] | None = None
    autoren: Annotated[
        list[Autor],
        Field(
            description="List of authors of the document. Could be a person, organisation or a parliamentary body"
        ),
    ]


class Station(BaseModel):
    api_id: Annotated[
        UUID | None,
        Field(
            description="optional, here for future references. Is generated by the server. If you set it use UUID version 5 with your collector id as namespace"
        ),
    ] = None
    touched_by: TouchedBy | None = None
    titel: Annotated[
        str | None,
        Field(
            description="optional title, if other data does not provide a proper description"
        ),
    ] = None
    zp_start: Annotated[
        AwareDatetime,
        Field(
            description="Date of the first action within this station. i.e.: First session of a committee",
            examples=["2024-01-01T00:00:00+00:00"],
        ),
    ]
    zp_modifiziert: Annotated[
        AwareDatetime | None,
        Field(
            description="Date of the last relevant action within this station. i.e.: last session of a committee",
            examples=["2024-01-01T00:00:00+00:00"],
        ),
    ] = None
    gremium: Gremium
    gremium_federf: Annotated[
        bool | None,
        Field(
            description="If the station if of type parl-ausschbsl, this field should be set if the committee is the main committee ('federführend')"
        ),
    ] = None
    link: Annotated[
        AnyUrl | None,
        Field(description="Link to a web page describing this NOT to a pdf document"),
    ] = None
    typ: Stationstyp
    trojanergefahr: Annotated[
        int | None,
        Field(description="Currently unused. Always set to null", ge=1, le=10),
    ] = None
    schlagworte: list[str] | None = None
    dokumente: list[Dokument | str]
    additional_links: list[AnyUrl] | None = None
    stellungnahmen: list[Dokument | str] | None = None


class Lobbyregeintrag(BaseModel):
    organisation: Autor
    interne_id: Annotated[
        str,
        Field(
            description="Interne ID des Lobbyregisters, notwendig für die bildung von Links"
        ),
    ]
    intention: Annotated[
        str,
        Field(
            description="Lobbyregistereintrag zu dem  Was und Warum man auf den Vorgang Einfluss nehmen will"
        ),
    ]
    link: Annotated[AnyUrl, Field(description="Direktlink zum Lobbyregistereintrag")]
    betroffene_drucksachen: Annotated[
        list[str],
        Field(
            description="Array with associated Drucksachennummern. Is not crossreferenced in the database and just added as dataset"
        ),
    ]


class Vorgang(BaseModel):
    api_id: Annotated[
        UUID,
        Field(
            description="Use UUID version 5 with your collector id as namespace",
            examples=["123e4567-e89b-12d3-a456-426614174000"],
        ),
    ]
    touched_by: TouchedBy | None = None
    titel: str
    kurztitel: str | None = None
    wahlperiode: Annotated[
        int, Field(description="number of the electoral period", ge=0)
    ]
    verfassungsaendernd: bool
    typ: Vorgangstyp
    ids: list[VgIdent] | None = None
    links: list[AnyUrl] | None = None
    initiatoren: Annotated[
        list[Autor],
        Field(
            description="List of persons or organisations, which initiated the Vorgang."
        ),
    ]
    stationen: list[Station]
    lobbyregister: list[Lobbyregeintrag] | None = None
    ressort: Ressort | None = None
    sachgebiete: list[Sachgebiet] | None = None


class Top(BaseModel):
    nummer: Annotated[int, Field(description="number of this item on the agenda", ge=0)]
    titel: str
    vorgang_id: Annotated[
        list[UUID] | None,
        Field(
            description="api ids of associated Vorgang objects. Is ignored at upload time, but passed on with the download after requests in the database"
        ),
    ] = None
    dokumente: Annotated[
        list[Dokument | str] | None,
        Field(description="Documents to be talked about in this TOP"),
    ] = None


class Sitzung(BaseModel):
    api_id: Annotated[
        UUID | None,
        Field(
            description="optional, here for future references. Is generated by the server. If you set it use UUID version 5 with your collector id as namespace"
        ),
    ] = None
    touched_by: TouchedBy | None = None
    titel: Annotated[str | None, Field(description="Title if applicable")] = None
    termin: Annotated[AwareDatetime, Field(examples=["2024-03-15T10:00:00+00:00"])]
    gremium: Gremium
    nummer: Annotated[int, Field(ge=0)]
    public: bool
    link: AnyUrl | None = None
    tops: list[Top]
    dokumente: Annotated[
        list[Dokument | str] | None,
        Field(description="Announcements, agendas and changed/amended agendas"),
    ] = None
    experten: Annotated[
        list[Autor] | None,
        Field(
            description="List of invited experts. if this is not null or empty, a session is a hearing."
        ),
    ] = None


class FtmDokumentPages(BaseModel):
    fileName: str | None = None
    title: str | None = None
    mimeType: Mime | None = None
    parent: str | None = None
    pdfHash: str | None = None
    pages: list[FtmDokumentPages] | None = None
    contentHash: str | None = None
    author: str | None = None
    generator: str | None = None
    crawler: str | None = None
    fileSize: Annotated[int | None, Field(ge=0)] = None
    extension: str | None = None
    encoding: str | None = None
    bodyText: str | None = None
    messageId: str | None = None
    language: str | None = None
    translatedLanguage: str | None = None
    translatedText: str | None = None
    date: AwareDatetime | None = None
    authoredAt: AwareDatetime | None = None
    publishedAt: AwareDatetime | None = None
    ancestors: list[dict[str, Any]] | None = None
    processingStatus: str | None = None
    processingError: str | None = None
    processingAgent: str | None = None
    processedAt: AwareDatetime | None = None
    proven: list[dict[str, Any]] | None = None
    name: str | None = None
    alias: str | None = None
    previousName: str | None = None
    weakAlias: str | None = None
    country: str | None = None
    summary: str | None = None
    notes: str | None = None
    description: str | None = None
    sourceUrl: AnyUrl | None = None
    publisher: str | None = None
    publisherUrl: AnyUrl | None = None
    alephUrl: AnyUrl | None = None
    wikipediaUrl: AnyUrl | None = None
    wikidataId: str | None = None
    keywords: list[str] | None = None
    topics: list[str] | None = None
    address: str | None = None
    addressEntity: dict[str, Any] | None = None
    program: str | None = None
    programId: str | None = None
    proof: dict[str, Any] | None = None
    indexText: str | None = None
    createdAt: AwareDatetime | None = None
    modifiedAt: AwareDatetime | None = None
    retrievedAt: AwareDatetime | None = None
    detectedLanguage: str | None = None
    detectedCountry: str | None = None
    namesMentioned: list[str] | None = None
    peopleMentioned: list[str] | None = None
    companiesMentioned: list[str] | None = None
    ibanMentioned: list[str] | None = None
    ipMentioned: list[str] | None = None
    locationMentioned: list[str] | None = None
    phoneMentioned: list[str] | None = None
    emailMentioned: list[str] | None = None
    provenIntervals: list[dict[str, Any]] | None = None
    relatedEntities: list[dict[str, Any]] | None = None
    documentedBy: dict[str, Any] | None = None
    noteEntities: dict[str, Any] | None = None
    sanctions: list[dict[str, Any]] | None = None
    candidateSimilars: list[dict[str, Any]] | None = None
    matchSimilars: list[dict[str, Any]] | None = None
    risks: list[dict[str, Any]] | None = None
    mentionedEntities: list[dict[str, Any]] | None = None
    unknownLinkTo: dict[str, Any] | None = None
    unknownLinkFrom: dict[str, Any] | None = None
    courtCase: list[dict[str, Any]] | None = None


FtmDokumentPages.model_rebuild()
