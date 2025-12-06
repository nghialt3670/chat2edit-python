from typing import List

from pydantic import BaseModel

from chat2edit.models import ExemplaryChatCycle


class Exemplar(BaseModel):
    cycles: List[ExemplaryChatCycle]
