from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Type, Union

from chat2edit.attachment import Attachment
from chat2edit.models import Phase


class ContextProvider(ABC):
    @abstractmethod
    def get_context(self) -> Dict[str, Union[Type, Callable]]:
        pass

    @abstractmethod
    def get_exemplars(self) -> List[Phase]:
        pass

    def attach(self, obj: Any) -> Attachment:
        return Attachment(obj)


class Llm(ABC):
    @abstractmethod
    async def generate(self, messages: List[str]) -> str:
        pass


class PromptStrategy(ABC):
    @abstractmethod
    def create_prompt(
        self, phases: List[Phase], context: Dict[str, Any], exemplars: List[Phase]
    ) -> str:
        pass

    @abstractmethod
    def get_refine_prompt(self) -> str:
        pass

    @abstractmethod
    def extract_code(self, text: str) -> str:
        pass
