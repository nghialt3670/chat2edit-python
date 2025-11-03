from typing import List

from pydantic import Field

from chat2edit.models import ContextualizedFeedback


class MismatchListParametersFeedback(ContextualizedFeedback):
    severity: str = Field(default="error")
    parameters: List[str]
    lengths: List[int]
