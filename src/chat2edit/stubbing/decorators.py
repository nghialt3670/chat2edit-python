from itertools import chain
from typing import Any, Iterable, Type

from chat2edit.constants import (
    CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY,
    CLASS_STUB_EXCLUDED_BASES_KEY,
    CLASS_STUB_EXCLUDED_METHODS_KEY,
    STUB_EXCLUDED_DECORATORS_KEY,
)


def extend_excluded_decorators(obj: Any, decorators: Iterable[str]) -> None:
    existing_decorators = getattr(obj, STUB_EXCLUDED_DECORATORS_KEY, [])
    setattr(
        obj,
        STUB_EXCLUDED_DECORATORS_KEY,
        list(chain(existing_decorators, decorators)),
    )


def exclude_bases(bases: Iterable[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_STUB_EXCLUDED_BASES_KEY, bases)
        extend_excluded_decorators(cls, ["exclude_bases"])
        return cls

    return decorator


def exclude_attributes(attributes: Iterable[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY, attributes)
        extend_excluded_decorators(cls, ["exclude_attributes"])
        return cls

    return decorator


def exclude_methods(methods: Iterable[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_STUB_EXCLUDED_METHODS_KEY, methods)
        extend_excluded_decorators(cls, ["exclude_methods"])
        return cls

    return decorator


def exclude_decorators(decorators: Iterable[str]):
    def decorator(cls: Type[Any]):
        extend_excluded_decorators(cls, chain(decorators, ["exclude_decorators"]))
        return cls

    return decorator
