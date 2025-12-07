from abc import ABC, abstractmethod
from typing import Any, Dict

from chat2edit.models import Message


class ContextStrategy(ABC):
    @abstractmethod
    def filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def contextualize_message(self, message: Message, context: Dict[str, Any]) -> Message:
        pass

    @abstractmethod
    def decontextualize_message(self, message: Message, context: Dict[str, Any]) -> Message:
        pass
