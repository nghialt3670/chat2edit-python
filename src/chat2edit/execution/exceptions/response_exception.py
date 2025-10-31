from chat2edit.models import ChatMessage


class ResponseException(Exception):
    def __init__(self, response: ChatMessage) -> None:
        super().__init__()
        self.response = response
