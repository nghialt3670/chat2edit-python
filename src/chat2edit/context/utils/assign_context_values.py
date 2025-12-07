from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from chat2edit.utils import to_snake_case


def assign_context_values(
    values: List[Any],
    context: Dict[str, Any],
    get_varname_prefix: Optional[Callable[[Any], str]] = None,
    max_varname_index: int = 100,
) -> List[str]:
    existing_varnames = set(context.keys())
    assigned_varnames = []

    for value in values:
        varname = get_varname(value, existing_varnames, get_varname_prefix, max_varname_index)
        existing_varnames.add(varname)
        assigned_varnames.append(varname)
        context[varname] = value

    return assigned_varnames


def get_varname(
    value: Any,
    existing_varnames: Set[str],
    get_varname_prefix: Optional[Callable[[Any], str]] = None,
    max_varname_index: int = 100,
) -> str:
    basename = get_varname_prefix(value) if get_varname_prefix else get_basename(value)

    i = 0
    while i < max_varname_index:
        if (varname := f"{basename}_{i}") not in existing_varnames:
            return varname
        i += 1

    unique_id = str(uuid4()).split("-")[0]
    return f"{basename}_{unique_id}"


def get_basename(value: Any) -> str:
    return to_snake_case(type(value).__name__).split("_").pop()
