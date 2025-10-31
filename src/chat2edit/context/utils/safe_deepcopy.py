from copy import deepcopy
from typing import Any, Dict


def safe_deepcopy(context: Dict[str, Any]) -> Dict[str, Any]:
    copied_context = {}

    for k, v in context.items():
        try:
            copied_context[k] = deepcopy(v)
        except:
            copied_context[k] = v

    return copied_context
