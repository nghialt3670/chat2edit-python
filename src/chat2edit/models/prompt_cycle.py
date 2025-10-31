from typing import List

from pydantic import BaseModel, Field

from chat2edit.models.execution_block import ExecutionBlock
from chat2edit.models.prompt_exchange import PromptExchange


class PromptCycle(BaseModel):
    exchanges: List[PromptExchange] = Field(default_factory=list)
    blocks: List[ExecutionBlock] = Field(default_factory=list)
