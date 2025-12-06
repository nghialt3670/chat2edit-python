from pydantic import Field

from chat2edit.models import Feedback


class IncompleteCycleFeedback(Feedback):
    severity: str = Field(default="info")
    incomplete: bool = Field(default=True)
