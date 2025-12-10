from typing import Annotated, Optional

from pydantic import BaseModel, Field

from chat2edit.models.feedback import FeedbackUnion
from chat2edit.models.message import Message


class ExemplaryExecutionBlock(BaseModel):
    generated_code: str
    # Use discriminated union so feedback is parsed into the right subclass
    feedback: Optional[Annotated[FeedbackUnion, Field(discriminator="type")]] = Field(
        default=None
    )
    response: Optional[Message] = Field(default=None)
    executed: bool = Field(default=True)  # Keep this field for backward compatibility
