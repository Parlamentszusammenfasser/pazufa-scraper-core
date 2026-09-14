from enum import Enum


class APIScope(str, Enum):
    ADMIN = "admin"
    COLLECTOR = "collector"
    KEYADDER = "keyadder"

    def __str__(self) -> str:
        return str(self.value)
