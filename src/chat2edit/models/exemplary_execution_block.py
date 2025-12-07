from typing import Optional

from pydantic import BaseModel, Field

from chat2edit.models.feedback import Feedback
from chat2edit.models.message import Message


class ExemplaryExecutionBlock(BaseModel):
    generated_code: str
    # Use Feedback base class to accept any Feedback subclass including custom ones
    # Pydantic will still validate based on the 'type' discriminator field
    feedback: Optional[Feedback] = Field(default=None)
    response: Optional[Message] = Field(default=None)
    executed: bool = Field(default=True)  # Keep this field for backward compatibility
