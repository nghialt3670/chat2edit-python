from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from chat2edit.models import ChatCycle, Exemplar
from chat2edit.models import LlmMessage


class PromptingStrategy(ABC):
    @abstractmethod
    def create_prompt(
        self,
        cycles: List[ChatCycle],
        exemplars: List[Exemplar],
        context: Dict[str, Any],
    ) -> LlmMessage:
        pass

    @abstractmethod
    def get_refine_prompt(self) -> LlmMessage:
        pass

    @abstractmethod
    def extract_code(self, text: str) -> Optional[str]:
        pass
