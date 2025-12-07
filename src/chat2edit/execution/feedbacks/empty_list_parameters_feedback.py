from typing import List, Literal

from pydantic import Field

from chat2edit.models import Feedback


class EmptyListParametersFeedback(Feedback):
    severity: Literal["info", "warning", "error"] = Field(default="error")
    parameters: List[str]
