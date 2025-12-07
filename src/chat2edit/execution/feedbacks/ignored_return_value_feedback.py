from typing import Literal

from pydantic import Field

from chat2edit.models import Feedback


class IgnoredReturnValueFeedback(Feedback):
    severity: Literal["info", "warning", "error"] = Field(default="error")
    value_type: str
