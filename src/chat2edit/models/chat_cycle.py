from typing import List, Optional

from pydantic import BaseModel, Field

from chat2edit.models.contextualized_message import ContextualizedMessage
from chat2edit.models.prompt_cycle import PromptCycle


class ChatCycle(BaseModel):
    request: ContextualizedMessage
    cycles: List[PromptCycle] = Field(default_factory=list)
