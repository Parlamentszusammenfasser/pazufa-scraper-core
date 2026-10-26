from enum import StrEnum


class Doktyp(StrEnum):
    ANFRAGE = "anfrage"
    ANTRAG = "antrag"
    ANTWORT = "antwort"
    BESCHLUSSEMPF = "beschlussempf"
    BESCHLUSSPROTOKOLL = "beschlussprotokoll"
    ECKPUNKTEPAPIER = "eckpunktepapier"
    ENTWURF = "entwurf"
    GESETZ = "gesetz"
    GUTACHTEN = "gutachten"
    INHALTSPROTOKOLL = "inhaltsprotokoll"
    MITTEILUNG = "mitteilung"
    PREPARL_ENTWURF = "preparl-entwurf"
    REDEPROTOKOLL = "redeprotokoll"
    SONSTIG = "sonstig"
    STELLUNGNAHME = "stellungnahme"
    TOPS = "tops"
    TOPS_AEND = "tops-aend"
    TOPS_ERGZ = "tops-ergz"

    def __str__(self) -> str:
        return str(self.value)
