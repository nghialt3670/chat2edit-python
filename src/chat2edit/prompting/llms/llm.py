from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from chat2edit.models import Message


class Llm(ABC):
    @abstractmethod
    async def generate(self, prompt: Message, history: List[Tuple[Message, Message]]) -> Message:
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass
