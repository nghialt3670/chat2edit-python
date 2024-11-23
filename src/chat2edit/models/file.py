from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class File:
    mimetype: str
    filename: str
    buffer: bytes
