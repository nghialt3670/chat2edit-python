from pydantic import Field

from chat2edit.models import ContextualizedFeedback


class IgnoredReturnValueFeedback(ContextualizedFeedback):
    severity: str = Field(default="error")
    function: str
    value_type: str
