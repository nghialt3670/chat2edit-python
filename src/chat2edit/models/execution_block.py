from typing import List, Optional

from pydantic import BaseModel, Field

from chat2edit.models.contextualized_feedback import ContextualizedFeedback
from chat2edit.models.contextualized_message import ContextualizedMessage
from chat2edit.models.execution_error import ExecutionError


class ExecutionBlock(BaseModel):
    generated_code: str
    processed_code: str
    executed: bool = Field(default=False)
    feedback: Optional[ContextualizedFeedback] = Field(default=None)
    response: Optional[ContextualizedMessage] = Field(default=None)
    error: Optional[ExecutionError] = Field(default=None)
    logs: List[str] = Field(default_factory=list)
