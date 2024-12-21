from itertools import chain
from typing import Any, Callable, Dict, Iterable, Type

from chat2edit.constants import (
    CLASS_ALIAS_KEY,
    CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY,
    CLASS_STUB_EXCLUDED_BASES_KEY,
    CLASS_STUB_EXCLUDED_METHODS_KEY,
    CLASS_STUB_MEMBER_ALIASES_KEY,
    FUNCTION_ALIAS_KEY,
    FUNCTION_STUB_PARAMETER_ALIASES_KEY,
    STUB_EXCLUDED_DECORATORS_KEY,
)


def _extend_excluded_decorators(obj: Any, decorators: Iterable[str]) -> None:
    existing_decorators = getattr(obj, STUB_EXCLUDED_DECORATORS_KEY, [])
    setattr(
        obj,
        STUB_EXCLUDED_DECORATORS_KEY,
        list(chain(existing_decorators, decorators)),
    )


def _extend_member_aliases(cls: Type[Any], aliases: Dict[str, str]) -> None:
    existing_aliases = getattr(cls, CLASS_STUB_MEMBER_ALIASES_KEY, {})
    existing_aliases.update(aliases)
    setattr(cls, CLASS_STUB_MEMBER_ALIASES_KEY, existing_aliases)


def _extend_parameter_aliases(func: Callable, aliases: Dict[str, str]) -> None:
    existing_aliases = getattr(func, FUNCTION_STUB_PARAMETER_ALIASES_KEY, {})
    existing_aliases.update(aliases)
    setattr(func, FUNCTION_STUB_PARAMETER_ALIASES_KEY, existing_aliases)


def exclude_bases(bases: Iterable[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_STUB_EXCLUDED_BASES_KEY, bases)
        _extend_excluded_decorators(cls, ["exclude_bases"])
        return cls

    return decorator


def exclude_attributes(attributes: Iterable[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY, attributes)
        _extend_excluded_decorators(cls, ["exclude_attributes"])
        return cls

    return decorator


def exclude_methods(methods: Iterable[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_STUB_EXCLUDED_METHODS_KEY, methods)
        _extend_excluded_decorators(cls, ["exclude_methods"])
        return cls

    return decorator


def exclude_decorators(decorators: Iterable[str]):
    def decorator(cls: Type[Any]):
        _extend_excluded_decorators(cls, chain(decorators, ["exclude_decorators"]))
        return cls

    return decorator


def class_alias(alias: str):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_ALIAS_KEY, alias)
        _extend_excluded_decorators(cls, ["class_alias"])
        return cls

    return decorator


def function_alias(alias: str):
    def decorator(func: Callable):
        setattr(func, FUNCTION_ALIAS_KEY, alias)
        _extend_excluded_decorators(func, ["function_alias"])
        return func

    return decorator


def member_aliases(aliases: Dict[str, str]):
    def decorator(cls: Type[Any]):
        _extend_member_aliases(cls, aliases)
        _extend_excluded_decorators(cls, ["member_aliases"])
        return cls

    return decorator


def parameter_aliases(aliases: Dict[str, str]):
    def decorator(func: Callable):
        _extend_parameter_aliases(func, aliases)
        _extend_excluded_decorators(func, ["parameter_aliases"])
        return func

    return decorator
