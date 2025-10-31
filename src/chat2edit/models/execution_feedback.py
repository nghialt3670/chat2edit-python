from typing import Any, List

from pydantic import Field

from chat2edit.models.feedback import Feedback


class ExecutionFeedback(Feedback):
    attachments: List[Any] = Field(default_factory=list)
