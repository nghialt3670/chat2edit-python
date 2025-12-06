from typing import Optional

from pydantic import BaseModel, Field

from chat2edit.models.chat_message import ChatMessage
from chat2edit.models.execution_feedback import ExecutionFeedback


class ExemplaryExecutionBlock(BaseModel):
    generated_code: str
    feedback: Optional[ExecutionFeedback] = Field(default=None)
    response: Optional[ChatMessage] = Field(default=None)
    exectuted: bool = Field(default=True) # Keep this field for backward compatibility
