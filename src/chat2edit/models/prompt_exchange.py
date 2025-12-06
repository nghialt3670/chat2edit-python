from typing import List, Optional

from pydantic import BaseModel, Field

from chat2edit.models.llm_message import LlmMessage
from chat2edit.models.prompt_error import PromptError


class PromptExchange(BaseModel):
    prompt: LlmMessage
    answer: LlmMessage = Field(default=None)
    error: Optional[PromptError] = Field(default=None)
    code: Optional[str] = Field(default=None)
