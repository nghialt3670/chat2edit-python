from typing import List

from pydantic import BaseModel, Field

from chat2edit.models.exemplary_prompt_cycle import ExemplaryPromptCycle
from chat2edit.models.message import Message


class ExemplaryChatCycle(BaseModel):
    request: Message
    cycles: List[ExemplaryPromptCycle] = Field(default_factory=list)
