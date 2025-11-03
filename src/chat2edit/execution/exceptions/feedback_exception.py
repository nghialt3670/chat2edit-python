from typing import Union

from chat2edit.models import ContextualizedFeedback, ExecutionFeedback


class FeedbackException(Exception):
    def __init__(
        self, feedback: Union[ExecutionFeedback, ContextualizedFeedback]
    ) -> None:
        super().__init__()
        self.feedback = feedback
