from pydantic import Field

from chat2edit.models import ContextualizedFeedback


class IncompleteCycleFeedback(ContextualizedFeedback):
    severity: str = Field(default="info")
    incomplete: bool = Field(default=True)
