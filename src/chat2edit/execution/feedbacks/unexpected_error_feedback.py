from typing import Literal

from pydantic import Field

from chat2edit.models import ExecutionError, Feedback


class UnexpectedErrorFeedback(Feedback):
    type: Literal["unexpected_error"] = "unexpected_error"
    severity: Literal["info", "warning", "error"] = Field(default="error")
    error: ExecutionError
