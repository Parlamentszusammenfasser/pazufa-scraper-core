from enum import Enum


class DokumentFormat(str, Enum):
    FTM = "ftm"
    PAZUFA = "pazufa"

    def __str__(self) -> str:
        return str(self.value)
