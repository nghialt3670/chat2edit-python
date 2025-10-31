from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chat2edit.models import (
    ChatMessage,
    ContextualizedFeedback,
    ContextualizedMessage,
    ExecutionFeedback,
)


class ContextStrategy(ABC):
    @abstractmethod
    def contextualize_message(
        self, message: ChatMessage, context: Dict[str, Any]
    ) -> ContextualizedMessage:
        pass

    @abstractmethod
    def contextualize_feedback(
        self, feedback: ExecutionFeedback, context: Dict[str, Any]
    ) -> ContextualizedFeedback:
        pass

    @abstractmethod
    def decontextualize_message(
        self, message: ContextualizedMessage, context: Dict[str, Any]
    ) -> ChatMessage:
        pass
