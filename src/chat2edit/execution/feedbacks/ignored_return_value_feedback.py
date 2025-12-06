from pydantic import Field

from chat2edit.models import Feedback


class IgnoredReturnValueFeedback(Feedback):
    severity: str = Field(default="error")
    value_type: str
