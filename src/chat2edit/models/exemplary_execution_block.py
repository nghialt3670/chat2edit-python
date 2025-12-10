from typing import Optional

from pydantic import BaseModel, Field, field_validator

from chat2edit.models.feedback import Feedback, get_feedback_class
from chat2edit.models.message import Message


class ExemplaryExecutionBlock(BaseModel):
    generated_code: str
    # Use Feedback base class to accept any Feedback subclass (including custom ones)
    # The validator will parse dict inputs into the correct Feedback subclass using the registry
    feedback: Optional[Feedback] = Field(default=None)
    response: Optional[Message] = Field(default=None)
    executed: bool = Field(default=True)  # Keep this field for backward compatibility

    @field_validator("feedback", mode="before")
    @classmethod
    def validate_feedback(cls, v):
        """Validate feedback, parsing dict inputs into the correct Feedback subclass."""
        if v is None:
            return None
        # If it's already a Feedback instance, return it as-is
        if isinstance(v, Feedback):
            return v
        # If it's a dict, look up the correct Feedback subclass from the registry
        if isinstance(v, dict):
            feedback_type = v.get("type")
            if feedback_type:
                feedback_class = get_feedback_class(feedback_type)
                if feedback_class:
                    # Parse using the specific Feedback subclass
                    return feedback_class.model_validate(v)
            # Fallback: try to parse as base Feedback
            return Feedback.model_validate(v)
        return v
