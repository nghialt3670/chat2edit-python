from typing import Literal

from pydantic import Field

from chat2edit.models import Feedback


class ModifiedAttachmentFeedback(Feedback):
    type: Literal["modified_attachment"] = "modified_attachment"
    severity: Literal["info", "warning", "error"] = Field(default="error")
    variable: str
    attribute: str
