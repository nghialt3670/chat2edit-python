from typing import Literal

from pydantic import Field

from chat2edit.models.feedback import Feedback


class IncompleteCycleFeedback(Feedback):
    type: Literal["incomplete_cycle"] = "incomplete_cycle"
    severity: Literal["info", "warning", "error"] = Field(default="info")
    incomplete: bool = Field(default=True)
