from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from chat2edit.models import ChatMessage, ExecutionError, ExecutionFeedback


class ExecutionStrategy(ABC):
    @abstractmethod
    def parse(self, code: str) -> List[str]:
        pass

    @abstractmethod
    def process(self, code: str, context: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def execute(self, code: str, context: Dict[str, Any]) -> Tuple[
        Optional[ExecutionError],
        Optional[ExecutionFeedback],
        Optional[ChatMessage],
        List[str],
    ]:
        pass
