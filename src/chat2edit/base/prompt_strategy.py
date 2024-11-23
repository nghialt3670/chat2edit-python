from abc import ABC, abstractmethod
from typing import List

from chat2edit.models.context import Context
from chat2edit.models.cycles import ChatCycle


class PromptStrategy(ABC):
    @abstractmethod
    def create_prompt(self, cycles: List[ChatCycle], context: Context) -> str:
        pass

    @abstractmethod
    def get_refine_prompt(self) -> str:
        pass

    @abstractmethod
    def extract_code(self, text: str) -> str:
        pass
