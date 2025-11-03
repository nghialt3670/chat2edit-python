from pydantic import Field

from chat2edit.models import ContextualizedFeedback, ExecutionError


class UnexpectedErrorFeedback(ContextualizedFeedback):
    severity: str = Field(default="error")
    error: ExecutionError
