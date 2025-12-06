from typing import List

from pydantic import Field

from chat2edit.models import Feedback


class EmptyListParametersFeedback(Feedback):
    severity: str = Field(default="error")
    parameters: List[str]
