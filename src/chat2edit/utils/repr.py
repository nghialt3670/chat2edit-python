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
