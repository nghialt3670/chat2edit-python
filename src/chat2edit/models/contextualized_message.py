from typing import List

from pydantic import Field

from chat2edit.models.message import Message


class ContextualizedMessage(Message):
    paths: List[str] = Field(default_factory=list)
