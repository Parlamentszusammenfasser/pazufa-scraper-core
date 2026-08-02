from enum import Enum


class Mime(str, Enum):
    APPLICATIONJSON = "application/json"
    APPLICATIONPDF = "application/pdf"
    TEXTHTML = "text/html"
    TEXTPLAIN = "text/plain"

    def __str__(self) -> str:
        return str(self.value)
