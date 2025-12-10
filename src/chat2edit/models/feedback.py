from typing import Literal, Optional

from pydantic import Field

from chat2edit.models.message import Message


class Feedback(Message):
    type: str  # Discriminator field - must be overridden by subclasses
    severity: Literal["info", "warning", "error"]
    function: Optional[str] = Field(default=None)
