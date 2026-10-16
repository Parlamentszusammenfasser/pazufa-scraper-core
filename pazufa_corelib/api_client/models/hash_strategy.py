from enum import StrEnum


class HashStrategy(StrEnum):
    SHA1BYTES = "sha1+bytes"
    SHA256BYTES = "sha256+bytes"
    SHA256TEXT = "sha256+text"

    def __str__(self) -> str:
        return str(self.value)
