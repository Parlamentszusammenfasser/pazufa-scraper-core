from enum import StrEnum


class APIScope(StrEnum):
    ADMIN = "admin"
    COLLECTOR = "collector"
    KEYADDER = "keyadder"

    def __str__(self) -> str:
        return str(self.value)
