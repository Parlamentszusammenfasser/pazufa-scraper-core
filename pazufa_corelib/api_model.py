"""Pydantic models for the PaZuFa API.

Based on automatic generation and augmented with handcrafted additions.
"""

from __future__ import annotations

import warnings
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from pydantic import AnyHttpUrl, Field, RootModel, model_validator

from pazufa_corelib._api_model_hardening import (
    PaZuFaBaseModel,
    Sha256Hex,
    TzDatetime,
    check_hash_combination,
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


class EnumerationNames(StrEnum):
    schlagworte = "schlagworte"
    stationstypen = "stationstypen"
    vorgangstypen = "vorgangstypen"
    parlamente = "parlamente"
    vgidtypen = "vgidtypen"
    dokumententypen = "dokumententypen"


class HashStrategy(StrEnum):
    sha256_bytes = "sha256+bytes"
    sha256_text = "sha256+text"
    sha1_bytes = "sha1+bytes"


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

class Sachgebiet(IntEnum):
    """Subject area of a Vorgang, inspired by the Parlamentsspiegel systematics.

    Corresponds to the `fqVSys` parameter in the Parlamentsspiegel search. The
    generated mirror names these members `integer_1000`, `integer_1010`, ...
    because the spec ships a bare integer enum with no `x-enum-varnames`, so the
    codegen falls back to `<type>_<value>`. The names here come from
    `normalization/mappings/sachgebiete.yaml`, which is the vocabulary the
    enrichment chain already resolves against.

    `tests/test_api_model_sachgebiete.py` pins the members against the YAML — if
    a spec bump changes the value set, add the vocabulary entry rather than
    editing this enum alone.
    """

    Staat_und_Politik = 1000
    Staatsaufbau = 1010
    Menschenrechte = 1030
    Nation = 1050
    Ideologien = 1060
    Politische_Kräfte = 1070
    Wahlen = 1080
    Parlament = 1100
    Abgeordnete = 1110
    Öffentliche_Verwaltung = 1200
    Bundesregierung = 1210
    Landesregierung = 1220
    Kommunale_Angelegenheiten = 1230
    Öffentlicher_Dienst = 1240
    Innere_Sicherheit = 1300
    Polizei = 1310
    Verfassungsschutz = 1320
    Ordnungsrecht = 1330
    Katastrophen__und_Zivilschutz = 1340
    Rettungswesen = 1350
    Verteidigung = 1400
    Wehrdienst = 1410
    Rüstung = 1420
    Abrüstung = 1430
    Außenpolitik = 1500
    Internationale_Beziehungen = 1510
    Internationale_Organisationen = 1520
    Entwicklungszusammenarbeit = 1530
    Europapolitik = 1540
    Europäische_Union = 1600
    Organe_der_EU = 1610
    Programme_der_EU = 1620
    Wirtschaft = 2000
    Gewerbliche_Wirtschaft = 2010
    Handel = 2020
    Dienstleistungen = 2030
    Versicherungen = 2040
    Mittelständische_Wirtschaft = 2050
    Außenwirtschaft = 2060
    Verbraucher = 2070
    Preis__und_Kartellrecht = 2080
    Gewerbeaufsicht = 2090
    Energie = 2100
    Fossile_Energien = 2110
    Kernenergie = 2120
    Erneuerbare_Energien = 2130
    Bergbau = 2200
    Technologie = 2300
    Arbeit_und_Beschäftigung = 2400
    Arbeitsmarkt = 2410
    Berufsausbildung = 2420
    Arbeitsentgelt = 2430
    Mitbestimmung = 2440
    Arbeitsbedingungen = 2450
    Standardisierung = 2500
    Normung = 2510
    Eich__und_Messwesen = 2520
    Vermessungs__und_Katasterwesen = 2530
    Verkehr = 2600
    Öffentlicher_Personenverkehr = 2610
    Güterverkehr = 2620
    Straßenverkehr = 2630
    Schienenverkehr = 2640
    Luftverkehr = 2650
    Schifffahrt = 2660
    Raumfahrt = 2700
    Bauwesen = 2800
    Verkehrswegebau = 2810
    Städtebau = 2820
    Wohnungswesen = 2830
    Wasserbau = 2840
    Recht = 3100
    Strafrecht = 3110
    Zivilrecht = 3120
    Öffentliches_Recht = 3130
    Urheberschutz = 3140
    Verfassungsgerichtsbarkeit = 3200
    Justiz = 3300
    Gerichte_und_Staatsanwaltschaften = 3310
    Justizverwaltung = 3320
    Justizvollzug = 3330
    Juristische_Berufe = 3400
    Bildung = 4100
    Schulen = 4200
    Lehrer = 4210
    Allgemeinbildende_Schulen = 4220
    Berufsbildende_Schulen = 4230
    Sonderpädagogik = 4240
    Privatschulen = 4250
    Frühkindliche_Bildung = 4260
    Hochschulwesen = 4300
    Universitäten = 4310
    Kunst__und_Musikhochschulen = 4320
    Hochschulen_für_angewandte_Wissenschaften = 4330
    Wissenschaft = 4400
    Erwachsenenbildung = 4500
    Gesellschaft = 5000
    Lebensgemeinschaften = 5010
    Sexuelle_Identität = 5020
    Kinder = 5030
    Frauen = 5040
    Menschen_mit_Behinderungen = 5050
    Alte_Menschen = 5060
    Ausländer = 5070
    Sonstige_gesellschaftliche_Gruppen = 5080
    Soziales = 5100
    Sozialversicherung = 5110
    Sozialleistungen = 5120
    Soziale_Einrichtungen = 5130
    Versorgung = 5140
    Pflege = 5150
    Gesundheit = 5200
    Gesundheitsschutz = 5210
    Gesundheitseinrichtungen = 5220
    Medizinische_Berufe = 5230
    Arzneimittel = 5240
    Rauschmittel = 5250
    Psychiatrie = 5260
    Tod = 5270
    Umwelt = 6100
    Natur = 6110
    Tier = 6120
    Boden = 6130
    Wasser = 6140
    Klima = 6150
    Schadstoffe = 6160
    Abfall = 6200
    Abwasser = 6300
    Raumordnung = 6400
    Ländlicher_Raum = 6410
    Landwirtschaft = 6500
    Landwirtschaftliche_Betriebe = 6510
    Agrarmarkt = 6520
    Landwirtschaftliche_Berufe = 6530
    Wald = 6600
    Jagd = 6700
    Ernährung = 6800
    Tierkrankheiten = 6900
    Kunst = 7100
    Denkmalschutz = 7200
    Religionsgemeinschaften = 7300
    Freizeit = 7400
    Messen = 7500
    Sport = 7600
    Informationsgesellschaft = 7700
    Printmedien = 7710
    Rundfunk = 7720
    Film = 7730
    Informations__und_Kommunikationstechnologien = 7740
    Datenschutz = 7750
    Statistik = 7800
    Abgaben = 8100
    Finanzverwaltung = 8200
    Öffentlicher_Haushalt = 8300
    Öffentliche_Schulden = 8310
    Öffentliches_Vermögen = 8320
    Haushaltskontrolle = 8330
    Finanzausgleich = 8340
    Öffentliche_Vergabe = 8350
    Finanzmarkt = 8400
    Vermögen = 8600
    Glücksspiel = 8700
    Stiftung = 8800
    Unbekannt = 9900
    ohne__Systematik = 9999


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


class Zusammenfassungstupel(PaZuFaBaseModel):
    inhalt: Annotated[
        str | None,
        Field(
            description="Content of the summary part",
            examples=[
                "Das Gesetz zur Haarfärbeverordnung dient der Umsetzung der EU-Richtline 42/69420 zur Schuppenfreiheit bei Eigenschaftsänderlichen Haarmodifikationen vor..."
            ],
        ),
    ] = None
    typ: Annotated[
        str | None,
        Field(
            description="Type of summary, if the summary is made up of parts\nNOTE: there are some reserved type names:\n- `full`        means summary of the full document without origin info\n- `full-llm`    means summary of the full document, made by llm\n- `full-extern` means summary of the full document, taken from an external source\n\nYou are free to add to these if required, just please stick to the ones available if\npossible",
            examples=["Basisinformationen"],
        ),
    ] = None


class DokumentHash(PaZuFaBaseModel):
    mime: Annotated[
        Mime,
        Field(
            description="The mime of the hashed content.\nIf sha256/1+bytes was used, must be application/pdf;\nIf sha256+text was used, must be text/plain"
        ),
    ]
    strategy: Annotated[
        HashStrategy,
        Field(
            description="The strategy used to compute the hash.\nsha256+text denotes that not the raw file, but the _exact_ volltext field\nof the document was hashed.\nAll text must be utf-8, remain stable under subsequent extraction,\nand mime must be set to text/plain or text/html."
        ),
    ]
    value: Annotated[
        str, Field(description="Hash value as string of hexadecimal octets")
    ]

    @model_validator(mode="after")
    def _check_hash_combination(self) -> DokumentHash:
        """Reject mime/strategy/digest combinations the specification excludes.

        The rule and its table live in `_api_model_hardening` — the strategy
        decides both the legal mimes and the digest length, which no per-field
        annotation can express. Only the hook belongs here. The digest is
        lowercased on the way through.
        """
        self.value = check_hash_combination(self.strategy, self.mime, self.value)
        return self


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


class HashWrapper(RootModel[Sha256Hex | list[DokumentHash]]):
    """Either the legacy bare digest or the explicit list of typed hashes.

    The bare string form is the backwards-compatible spelling of
    ``sha256+bytes`` (see the ``hash`` field of `Dokument`), so it is validated
    as a sha256 digest rather than as a free string — the generated mirror types
    it as a plain ``str`` and would let a truncated or sha1 digest through.
    """

    root: Sha256Hex | list[DokumentHash]


class ZusammenfassungWrapper(RootModel[str | list[Zusammenfassungstupel]]):
    root: str | list[Zusammenfassungstupel]


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
        HashWrapper,
        Field(
            description="Wrapper that allows for legacy Hashes"
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
    subdoc_id: Annotated[
        int | None,
        Field(
            description="If a document contains more than one semantically closed document (x opinions in a collected file for example)\nthis denotes the index of the sub-file in question. They can potentially share a hash.",
            ge=0,
        ),
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
    zusammenfassung: ZusammenfassungWrapper | None = None

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
    ressort: Ressort | None = None
    sachgebiete: list[Sachgebiet] | None = None
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
