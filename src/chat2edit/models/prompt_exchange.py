from typing import Optional

from pydantic import Field

from chat2edit.models.exemplary_prompt_exchange import ExemplaryPromptExchange
from chat2edit.models.message import Message
from chat2edit.models.prompt_error import PromptError


class PromptExchange(ExemplaryPromptExchange):
    prompt: Message
    error: Optional[PromptError] = Field(default=None)
    code: Optional[str] = Field(default=None)
