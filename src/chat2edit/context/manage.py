from typing import Any, Dict, List, Set
from uuid import uuid4

from chat2edit.constants import MAX_VARNAME_SEARCH_INDEX
from chat2edit.context.attachment import Attachment
from chat2edit.context.utils import to_snake_case


def assign(values: List[Any], context: Dict[str, Any]) -> List[str]:
    existing_varnames = set(context.keys())
    assigned_varnames = []

    for value in values:
        varname = _find_suitable_varname(value, existing_varnames)
        existing_varnames.add(varname)
        assigned_varnames.append(varname)
        context[varname] = value

    return assigned_varnames


def _get_value_basename(value: Any) -> str:
    if isinstance(value, Attachment) and value.__basename__:
        return value.__basename__

    camel_clsname = type(value).__name__
    snake_clsname = to_snake_case(camel_clsname)

    return snake_clsname.split("_").pop()


def _find_suitable_varname(value: Any, existing_varnames: Set[str]) -> str:
    basename = _get_value_basename(value)

    i = 0

    while i < MAX_VARNAME_SEARCH_INDEX:
        if (varname := f"{basename}_{i}") not in existing_varnames:
            return varname

        i += 1

    i = str(uuid4()).split("_").pop()
    return f"{basename}_{i}"
