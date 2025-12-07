from typing import List, Literal

from pydantic import Field

from chat2edit.models import Feedback


class MismatchListParametersFeedback(Feedback):
    type: Literal["mismatch_list_parameters"] = "mismatch_list_parameters"
    severity: Literal["info", "warning", "error"] = Field(default="error")
    parameters: List[str]
    lengths: List[int]
