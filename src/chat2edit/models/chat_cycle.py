from typing import List

from pydantic import BaseModel, Field

from chat2edit.models.message import Message
from chat2edit.models.prompt_cycle import PromptCycle


class ChatCycle(BaseModel):
    request: Message
    cycles: List[PromptCycle] = Field(default_factory=list)
