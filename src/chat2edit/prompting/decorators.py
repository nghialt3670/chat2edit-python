from functools import wraps
from typing import Any, Callable, List, Optional, Type

from chat2edit.constants import CLASS_OR_FUNCTION_STUB_KEY, PYDANTIC_MODEL_STUB_EXCLUDES
from chat2edit.utils.repr import get_class_stub, get_function_stub


def declare_class(excludes: List[str] = []):
    def decorator(cls: Type[Any]):
        stub = get_class_stub(cls, excludes)
        setattr(cls, CLASS_OR_FUNCTION_STUB_KEY, stub)
        return cls

    return decorator


def declare_function(doc: Optional[str] = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        stub = get_function_stub(func)
        setattr(wrapper, CLASS_OR_FUNCTION_STUB_KEY, stub)
        wrapper.__doc__ = doc

        return wrapper

    return decorator


declare_pydantic_class = declare_class(PYDANTIC_MODEL_STUB_EXCLUDES)
