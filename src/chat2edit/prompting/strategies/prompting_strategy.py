from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from chat2edit.models import ChatCycle, Exemplar, Message


class PromptingStrategy(ABC):
    @abstractmethod
    def create_prompt(
        self,
        cycles: List[ChatCycle],
        exemplars: List[Exemplar],
        context: Dict[str, Any],
    ) -> Message:
        pass

    @abstractmethod
    def get_refine_prompt(self) -> Message:
        pass

    @abstractmethod
    def extract_code(self, text: str) -> Optional[str]:
        pass
