from enum import StrEnum


class EnumerationNames(StrEnum):
    DOKUMENTENTYPEN = "dokumententypen"
    PARLAMENTE = "parlamente"
    SCHLAGWORTE = "schlagworte"
    STATIONSTYPEN = "stationstypen"
    VGIDTYPEN = "vgidtypen"
    VORGANGSTYPEN = "vorgangstypen"

    def __str__(self) -> str:
        return str(self.value)
