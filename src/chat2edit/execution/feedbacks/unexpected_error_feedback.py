from pydantic import Field

from chat2edit.models import ExecutionError, Feedback


class UnexpectedErrorFeedback(Feedback):
    severity: str = Field(default="error")
    error: ExecutionError
