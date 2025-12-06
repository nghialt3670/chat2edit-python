from typing import List

from pydantic import BaseModel, Field

from chat2edit.models.exemplary_execution_block import ExemplaryExecutionBlock
from chat2edit.models.exemplary_prompt_exchange import ExemplaryPromptExchange


class ExemplaryPromptCycle(BaseModel):
    exchanges: List[ExemplaryPromptExchange] = Field(default_factory=list)
    blocks: List[ExemplaryExecutionBlock] = Field(default_factory=list)
