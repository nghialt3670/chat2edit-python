from pydantic import BaseModel

from chat2edit.models.message import Message


class ExemplaryPromptExchange(BaseModel):
    answer: Message
