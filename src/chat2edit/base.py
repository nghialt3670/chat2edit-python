from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chat2edit.attachment import Attachment
from chat2edit.models import ChatCycle, Context


class ContextProvider(ABC):
    @abstractmethod
    def get_context(self) -> Context:
        pass

    @abstractmethod
    def attach(self, obj: Any) -> Attachment:
        pass


class Llm(ABC):
    @abstractmethod
    async def generate(self, messages: List[str]) -> str:
        pass


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
