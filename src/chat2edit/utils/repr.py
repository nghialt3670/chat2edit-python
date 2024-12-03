import re
from typing import Any


def anno_repr(anno: Any) -> str:
    """Generate a cleaner representation for an annotation."""

    if anno == Any:
        return "Any"

    if hasattr(anno, "__origin__"):
        origin_repr = anno.__origin__.__name__.capitalize()

        if hasattr(anno, "__args__"):
            args_repr = ", ".join(map(anno_repr, anno.__args__))
            return f"{origin_repr}[{args_repr}]"

        return origin_repr

    elif isinstance(anno, type):
        return str(anno.__name__)

    else:
        return str(anno)


def to_snake_case(text: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def create_obj_basename(obj: Any) -> str:
    return to_snake_case(obj.__class__.__name__)
