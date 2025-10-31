from typing import List

from pydantic import Field

from chat2edit.models.message import Message
from chat2edit.models.timestamped_model import TimestampedModel


class ContextualizedMessage(Message):
    paths: List[str] = Field(default_factory=list)
