from typing import Any, List

from pydantic import Field

from chat2edit.models.timestamped_model import TimestampedModel


class Message(TimestampedModel):
    text: str = Field(default="")
    attachments: List[Any] = Field(default_factory=list)
    contextualized: bool = Field(default=False)
