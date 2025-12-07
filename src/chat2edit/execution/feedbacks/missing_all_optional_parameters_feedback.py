from typing import List, Literal

from pydantic import Field

from chat2edit.models.feedback import Feedback


class MissingAllOptionalParametersFeedback(Feedback):
    type: Literal["missing_all_optional_parameters"] = "missing_all_optional_parameters"
    severity: Literal["info", "warning", "error"] = Field(default="error")
    parameters: List[str]
