from pydantic import BaseModel

from chat2edit.models.llm_message import LlmMessage


class ExemplaryPromptExchange(BaseModel):
    answer: LlmMessage
