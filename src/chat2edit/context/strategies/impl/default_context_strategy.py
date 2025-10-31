from typing import Any, Dict, List, Set
from uuid import uuid4

from chat2edit.context.attachments import Attachment
from chat2edit.context.strategies.context_strategy import ContextStrategy
from chat2edit.context.utils import path_to_value
from chat2edit.models import (
    ChatMessage,
    ContextualizedFeedback,
    ContextualizedMessage,
    ExecutionFeedback,
)
from chat2edit.utils import to_snake_case

MAX_VARNAME_SEARCH_INDEX = 100


class DefaultContextStrategy(ContextStrategy):
    def contextualize_message(
        self, message: ChatMessage, context: Dict[str, Any]
    ) -> ContextualizedMessage:
        return ContextualizedMessage(
            text=message.text,
            attachments=self._assign_attachments(message.attachments, context),
        )

    def contextualize_feedback(
        self, feedback: ExecutionFeedback, context: Dict[str, Any]
    ) -> ContextualizedFeedback:
        return ContextualizedFeedback(
            text=feedback.text,
            attachments=self._assign_attachments(feedback.attachments, context),
        )

    def decontextualize_message(
        self, message: ContextualizedMessage, context: Dict[str, Any]
    ) -> ChatMessage:
        return ChatMessage(
            text=message.text,
            attachments=[path_to_value(path, context) for path in message.paths],
        )

    def _assign_attachments(
        self, attachments: List[Attachment], context: Dict[str, Any]
    ) -> List[str]:
        existing_varnames = set(context.keys())
        assigned_varnames = []

        for attachment in attachments:
            varname = self._find_suitable_varname(attachment, existing_varnames)
            existing_varnames.add(varname)
            assigned_varnames.append(varname)
            context[varname] = attachment

        return assigned_varnames

    def _get_attachment_basename(self, attachment: Attachment) -> str:
        return (
            attachment.__basename__
            if attachment.__basename__
            else to_snake_case(type(attachment).__name__).split("_").pop()
        )

    def _find_suitable_varname(
        self, attachment: Attachment, existing_varnames: Set[str]
    ) -> str:
        basename = self._get_attachment_basename(attachment)

        i = 0

        while i < MAX_VARNAME_SEARCH_INDEX:
            if (varname := f"{basename}_{i}") not in existing_varnames:
                return varname

            i += 1

        i = str(uuid4()).split("_").pop()
        return f"{basename}_{i}"
