from typing import Literal, Optional

from pydantic import Field

from chat2edit.models.message import Message


class Feedback(Message):
    severity: Literal["info", "warning", "error"]
    function: Optional[str] = Field(default=None)
