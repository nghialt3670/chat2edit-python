from chat2edit.models import Message


class ResponseException(Exception):
    def __init__(self, response: Message) -> None:
        super().__init__()
        self.response = response
