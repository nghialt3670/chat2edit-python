from typing import Literal

from pydantic import Field

from chat2edit.models import Feedback


class IncompleteCycleFeedback(Feedback):
    severity: Literal["info", "warning", "error"] = Field(default="info")
    incomplete: bool = Field(default=True)
