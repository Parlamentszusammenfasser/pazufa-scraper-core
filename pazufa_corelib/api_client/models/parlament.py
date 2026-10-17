from enum import StrEnum


class Parlament(StrEnum):
    BB = "BB"
    BE = "BE"
    BR = "BR"
    BT = "BT"
    BV = "BV"
    BW = "BW"
    BY = "BY"
    EK = "EK"
    HB = "HB"
    HE = "HE"
    HH = "HH"
    MV = "MV"
    NI = "NI"
    NW = "NW"
    RP = "RP"
    SH = "SH"
    SL = "SL"
    SN = "SN"
    ST = "ST"
    TH = "TH"

    def __str__(self) -> str:
        return str(self.value)
