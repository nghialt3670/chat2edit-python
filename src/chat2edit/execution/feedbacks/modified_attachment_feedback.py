from pydantic import Field

from chat2edit.models import Feedback


class ModifiedAttachmentFeedback(Feedback):
    severity: str = Field(default="error")
    variable: str
    attribute: str
