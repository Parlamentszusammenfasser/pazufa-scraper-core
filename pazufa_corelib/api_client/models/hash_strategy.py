from enum import Enum


class HashStrategy(str, Enum):
    SHA1BYTES = "sha1+bytes"
    SHA256BYTES = "sha256+bytes"
    SHA256TEXT = "sha256+text"

    def __str__(self) -> str:
        return str(self.value)
