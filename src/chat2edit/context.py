from typing import Any, Dict, Set
from uuid import uuid4

from chat2edit.base import ContextProvider
from chat2edit.constants import MAX_VARNAME_SEARCH_INDEX
from chat2edit.models import AssignedAttachment, Attachment, Message
from chat2edit.utils.context import path_to_obj
from chat2edit.utils.repr import to_snake_case


def assign_attachment(
    attachment: Attachment, exec_context: Dict[str, Any]
) -> AssignedAttachment:
    existing_varnames = set(exec_context.keys())

    basename = attachment.__basename__ or _create_default_basename(attachment)
    varname = _find_suitable_varname(basename, existing_varnames)
    existing_varnames.add(varname)
    exec_context[varname] = attachment

    assigned_attr_paths = [f"{varname}{path}" for path in attachment.attr_paths]

    assigned_query_objs = []
    for obj in attachment.__queryobjs__:
        obj_basename = obj.__basename__ or _create_default_basename(obj)
        obj_varname = _find_suitable_varname(obj_basename, existing_varnames)
        existing_varnames.add(obj_varname)
        exec_context[obj_varname] = obj
        assigned_query_objs.append(
            AssignedAttachment(type=obj.__class__, path=obj_varname)
        )

    return AssignedAttachment(
        type=attachment.__class__,
        path=varname,
        attr_paths=assigned_attr_paths,
        query_objs=assigned_query_objs,
    )


def _create_default_basename(attachment: Attachment) -> str:
    return to_snake_case(attachment.__class__.__name__).split("_").pop()


def _find_suitable_varname(basename: str, existing_varnames: Set[str]) -> str:
    idx = 0

    while idx < MAX_VARNAME_SEARCH_INDEX:
        if varname := f"{basename}{idx}" not in existing_varnames:
            return varname

        idx += 1

    return f"{basename}_{str(uuid4()).split("_").pop()}"


def assign_message(
    message: Message, exec_context: Dict[str, Any], provider: ContextProvider
) -> Message:
    return Message(
        text=message.text,
        attachments=[
            assign_attachment(att, exec_context) for att in message.attachments
        ],
    )


def create_message(message: Message, exec_context: Dict[str, Any]) -> Message:
    return Message(
        text=message.text,
        attachments=[
            path_to_obj(exec_context, att.path) for att in message.attachments
        ],
    )
