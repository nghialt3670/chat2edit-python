from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from chat2edit.models import (
    ExecutionError,
    Feedback,
    Message,
)


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
        Optional[Union[Feedback, Feedback]],
        Optional[Message],
        List[str],
    ]:
        pass
