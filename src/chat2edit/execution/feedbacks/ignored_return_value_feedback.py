from typing import Literal

from pydantic import Field

from chat2edit.models.feedback import Feedback


class IgnoredReturnValueFeedback(Feedback):
    type: Literal["ignored_return_value"] = "ignored_return_value"
    severity: Literal["info", "warning", "error"] = Field(default="error")
    value_type: str
