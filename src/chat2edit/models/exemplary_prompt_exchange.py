from typing import Optional

from pydantic import BaseModel, Field

from chat2edit.models.message import Message


class ExemplaryPromptExchange(BaseModel):
    answer: Optional[Message] = Field(default=None)
