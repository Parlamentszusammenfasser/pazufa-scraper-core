from enum import Enum


class Vorgangstyp(str, Enum):
    BU_ANTRAG_BWEINSATZ = "bu-antrag-bweinsatz"
    BU_EINSPRUCH_INIBREG = "bu-einspruch-inibreg"
    BU_EINSPRUCH_INIBREG_HAUSHALT = "bu-einspruch-inibreg-haushalt"
    BU_EINSPRUCH_INIBREG_INTVERTRAG = "bu-einspruch-inibreg-intvertrag"
    BU_EINSPRUCH_INISONST = "bu-einspruch-inisonst"
    BU_EINSPRUCH_INISONST_INTVERTRAG = "bu-einspruch-inisonst-intvertrag"
    BU_ZUSTIMMUNG_INIBREG = "bu-zustimmung-inibreg"
    BU_ZUSTIMMUNG_INIBREG_HAUSHALT = "bu-zustimmung-inibreg-haushalt"
    BU_ZUSTIMMUNG_INIBREG_INTVERTRAG = "bu-zustimmung-inibreg-intvertrag"
    BU_ZUSTIMMUNG_INISONST = "bu-zustimmung-inisonst"
    BU_ZUSTIMMUNG_INISONST_INTVERTRAG = "bu-zustimmung-inisonst-intvertrag"
    BW_EINSATZ = "bw-einsatz"
    GG_LAND_PARL = "gg-land-parl"
    GG_LAND_VOLK = "gg-land-volk"
    SONSTIG = "sonstig"

    def __str__(self) -> str:
        return str(self.value)
