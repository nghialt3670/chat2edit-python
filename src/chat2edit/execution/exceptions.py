from chat2edit.models import Feedback, Message


class FeedbackException(Exception):
    def __init__(self, feedback: Feedback) -> None:
        super().__init__()
        self.feedback = feedback


class ResponseException(Exception):
    def __init__(self, response: Message) -> None:
        super().__init__()
        self.response = response
