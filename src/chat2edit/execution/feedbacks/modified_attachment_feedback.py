from pydantic import Field

from chat2edit.models import ContextualizedFeedback


class ModifiedAttachmentFeedback(ContextualizedFeedback):
    severity: str = Field(default="error")
    variable: str
    attribute: str
