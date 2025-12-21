from typing import Any, Dict, List

from chat2edit.context.strategies.context_strategy import ContextStrategy
from chat2edit.context.utils import assign_context_values, path_to_value
from chat2edit.models import Message


class DefaultContextStrategy(ContextStrategy):
    def filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return context

    def contextualize_message(self, message: Message, context: Dict[str, Any]) -> Message:
        contextualized_attachments = self.contextualize_message_attachments(message.attachments, context)
        return Message(
            timestamp=message.timestamp,
            text=self.contextualize_message_text(message.text, context),
            attachments=contextualized_attachments,
            contextualized=True,
        )

    def decontextualize_message(self, message: Message, context: Dict[str, Any]) -> Message:
        return Message(
            text=self.decontextualize_message_text(message.text, context),
            attachments=self.decontextualize_message_attachments(message.attachments, context),
            contextualized=False,
        )

    def contextualize_message_text(self, text: str, context: Dict[str, Any]) -> str:
        return text

    def decontextualize_message_text(self, text: str, context: Dict[str, Any]) -> str:
        return text

    def contextualize_message_attachments(
        self, attachments: List[Any], context: Dict[str, Any]
    ) -> List[str]:
        return assign_context_values(attachments, context)

    def decontextualize_message_attachments(
        self, attachments: List[str], context: Dict[str, Any]
    ) -> List[Any]:
        return [path_to_value(path, context) for path in attachments]
