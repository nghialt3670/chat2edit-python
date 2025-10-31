from typing import List, Optional

from pydantic import BaseModel, Field

from chat2edit.models.prompt_error import PromptError
from chat2edit.prompting.llms.llm_message import LlmMessage


class PromptExchange(BaseModel):
    prompt: LlmMessage
    answers: List[LlmMessage] = Field(default_factory=list)
    error: Optional[PromptError] = Field(default=None)
    code: Optional[str] = Field(default=None)
