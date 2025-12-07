from typing import Any, Dict, List, Set
from uuid import uuid4

from chat2edit.context.strategies.context_strategy import ContextStrategy
from chat2edit.context.utils import path_to_value
from chat2edit.models import (
    Feedback,
    Message,
)
from chat2edit.utils import to_snake_case

MAX_VARNAME_SEARCH_INDEX = 100


class DefaultContextStrategy(ContextStrategy):
    def filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return context

    def contextualize_message(self, message: Message, context: Dict[str, Any]) -> Message:
        return Message(
            text=self.contextualize_text(message.text, context),
            attachments=self.contextualize_attachments(message.attachments, context),
            contextualized=True,
        )

    def contextualize_feedback(self, feedback: Feedback, context: Dict[str, Any]) -> Feedback:
        return Feedback(
            text=self.contextualize_text(feedback.text, context),
            attachments=self.contextualize_attachments(feedback.attachments, context),
            contextualized=True,
            severity=feedback.severity,
            function=feedback.function,
        )

    def decontextualize_message(self, message: Message, context: Dict[str, Any]) -> Message:
        return Message(
            text=self.decontextualize_text(message.text, context),
            attachments=self.decontextualize_attachments(message.attachments, context),
            contextualized=False,
        )

    def contextualize_text(self, text: str, context: Dict[str, Any]) -> str:
        return text

    def decontextualize_text(self, text: str, context: Dict[str, Any]) -> str:
        return text

    def contextualize_attachments(
        self, attachments: List[Any], context: Dict[str, Any]
    ) -> List[str]:
        existing_varnames = set(context.keys())
        assigned_varnames = []

        for attachment in attachments:
            varname = self._find_suitable_varname(attachment, existing_varnames)
            existing_varnames.add(varname)
            assigned_varnames.append(varname)
            context[varname] = attachment

        return assigned_varnames

    def decontextualize_attachments(
        self, attachments: List[str], context: Dict[str, Any]
    ) -> List[Any]:
        return [path_to_value(path, context) for path in attachments]

    def get_attachment_basename(self, attachment: Any) -> str:
        return to_snake_case(type(attachment).__name__).split("_").pop()

    def _find_suitable_varname(self, attachment: Any, existing_varnames: Set[str]) -> str:
        basename = self.get_attachment_basename(attachment)

        i = 0

        while i < MAX_VARNAME_SEARCH_INDEX:
            if (varname := f"{basename}_{i}") not in existing_varnames:
                return varname

            i += 1

        unique_id = str(uuid4()).split("-")[0]
        return f"{basename}_{unique_id}"
