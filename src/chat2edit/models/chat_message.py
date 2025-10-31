from typing import Any, List

from chat2edit.models.message import Message


class ChatMessage(Message):
    attachments: List[Any]
