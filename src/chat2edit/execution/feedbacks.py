from typing import Optional

from pydantic import Field

from chat2edit.models import Error, Feedback, Severity


class InvalidParameterTypeFeedback(Feedback):
    severity: Severity = Field(default="error")
    function: str
    parameter: str
    expected_type: str
    received_type: str


class ModifiedAttachmentFeedback(Feedback):
    severity: Severity = Field(default="error")
    variable: str
    attribute: str


class IgnoredReturnValueFeedback(Feedback):
    severity: Severity = Field(default="error")
    function: str
    value_type: str


class UnexpectedErrorFeedback(Feedback):
    severity: Severity = Field(default="error")
    function: Optional[str] = Field(default=None)
    error: Error


class IncompleteCycleFeedback(Feedback):
    severity: Severity = Field(default="info")
    incomplete: bool = Field(default=True)
