from chat2edit.models import ExecutionFeedback


class FeedbackException(Exception):
    def __init__(self, feedback: ExecutionFeedback) -> None:
        super().__init__()
        self.feedback = feedback
