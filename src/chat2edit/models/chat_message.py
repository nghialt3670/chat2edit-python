from typing import Any, List

from pydantic import Field

from chat2edit.models.message import Message


class ChatMessage(Message):
    attachments: List[Any] = Field(default_factory=list)
