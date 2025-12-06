from typing import List

from pydantic import BaseModel, Field

from chat2edit.models.chat_message import ChatMessage
from chat2edit.models.exemplary_prompt_cycle import ExemplaryPromptCycle


class ExemplaryChatCycle(BaseModel):
    request: ChatMessage
    cycles: List[ExemplaryPromptCycle] = Field(default_factory=list)
