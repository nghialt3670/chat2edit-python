from typing import List

from pydantic import BaseModel

from chat2edit.models.exemplary_chat_cycle import ExemplaryChatCycle


class Exemplar(BaseModel):
    cycles: List[ExemplaryChatCycle]
