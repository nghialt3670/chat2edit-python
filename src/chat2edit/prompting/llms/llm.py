from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from chat2edit.models import LlmMessage


class Llm(ABC):
    @abstractmethod
    async def generate(
        self, prompt: LlmMessage, history: List[Tuple[LlmMessage, LlmMessage]]
    ) -> LlmMessage:
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        pass
