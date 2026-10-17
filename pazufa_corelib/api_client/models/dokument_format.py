from enum import StrEnum


class DokumentFormat(StrEnum):
    FTM = "ftm"
    PAZUFA = "pazufa"

    def __str__(self) -> str:
        return str(self.value)
