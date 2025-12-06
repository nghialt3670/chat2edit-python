from pydantic import Field

from chat2edit.models import Feedback


class InvalidParameterTypeFeedback(Feedback):
    severity: str = Field(default="error")
    parameter: str
    expected_type: str
    received_type: str
