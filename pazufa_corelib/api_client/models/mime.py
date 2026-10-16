from enum import StrEnum


class Mime(StrEnum):
    APPLICATIONJSON = "application/json"
    APPLICATIONPDF = "application/pdf"
    TEXTHTML = "text/html"
    TEXTPLAIN = "text/plain"

    def __str__(self) -> str:
        return str(self.value)
