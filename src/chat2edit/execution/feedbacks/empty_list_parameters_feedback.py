from typing import List, Literal

from pydantic import Field

from chat2edit.models.feedback import Feedback


class EmptyListParametersFeedback(Feedback):
    type: Literal["empty_list_parameters"] = "empty_list_parameters"
    severity: Literal["info", "warning", "error"] = Field(default="error")
    parameters: List[str]
