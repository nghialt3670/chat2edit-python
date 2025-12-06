from typing import Optional

from pydantic import BaseModel, Field

from chat2edit.models.feedback import Feedback
from chat2edit.models.message import Message


class ExemplaryExecutionBlock(BaseModel):
    generated_code: str
    feedback: Optional[Feedback] = Field(default=None)
    response: Optional[Message] = Field(default=None)
    exectuted: bool = Field(default=True)  # Keep this field for backward compatibility
