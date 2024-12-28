from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chat2edit.models import ChatCycle


class ContextProvider(ABC):
    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_exemplars(self) -> List[ChatCycle]:
        pass


class Llm(ABC):
    @abstractmethod
    async def generate(self, messages: List[str]) -> str:
        pass


class PromptStrategy(ABC):
    @abstractmethod
    def create_prompt(
        self,
        cycles: List[ChatCycle],
        exemplars: List[ChatCycle],
        context: Dict[str, Any],
    ) -> str:
        pass

    @abstractmethod
    def get_refine_prompt(self) -> str:
        pass

    @abstractmethod
    def extract_code(self, text: str) -> str:
        pass
