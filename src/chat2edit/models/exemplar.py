from typing import List

from pydantic import BaseModel

from chat2edit.models import ChatCycle


class Exemplar(BaseModel):
    cycles: List[ChatCycle]
