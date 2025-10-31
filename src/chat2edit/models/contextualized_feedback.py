from typing import List

from pydantic import Field

from chat2edit.models.feedback import Feedback


class ContextualizedFeedback(Feedback):
    paths: List[str] = Field(default_factory=list)
