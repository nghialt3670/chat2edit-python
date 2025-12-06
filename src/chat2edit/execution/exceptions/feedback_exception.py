from chat2edit.models import Feedback


class FeedbackException(Exception):
    def __init__(self, feedback: Feedback) -> None:
        super().__init__()
        self.feedback = feedback
