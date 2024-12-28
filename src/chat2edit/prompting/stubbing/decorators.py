import inspect
from functools import wraps
from typing import Any, Callable, Dict, List, Type

from annotated_types import T

STUBBING_DECORATORS = {
    "alias",
    "include_decorators",
    "exclude_decorators",
    "include_bases",
    "exclude_bases",
    "include_attributes",
    "exclude_attributes",
    "include_methods",
    "exclude_methods",
    "base_aliases",
    "attribute_aliases",
    "parameter_aliases",
    "exclude_docstring",
    "exclude_coroutine",
}


def alias(alias: str):
    def decorator(target: Any):
        return target

    return decorator


def include_decorators(decorators: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def exclude_decorators(decorators: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def include_bases(bases: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def exclude_bases(bases: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def include_attributes(attributes: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def exclude_attributes(attributes: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def include_methods(methods: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def exclude_methods(methods: List[str]):
    def decorator(target: Any):
        return target

    return decorator


def base_aliases(mappings: Dict[str, str]):
    def decorator(target: Any):
        return target

    return decorator


def attribute_aliases(mappings: Dict[str, str]):
    reversed_mappings = {v: k for k, v in mappings.items()}

    def decorator(cls: Type[T]) -> Type[T]:
        original_getattribute = cls.__getattribute__
        original_setattr = cls.__setattr__

        # if map_func:
        #     hints = get_type_hints(cls)
        #     for attr in hints:
        #         if attr.startswith("_"):
        #             continue

        #         alias = map_func(attr)
        #         if alias != attr:
        #             reversed_mappings[alias] = attr

        #     if hasattr(cls, "__init__"):
        #         init_hints = get_type_hints(cls.__init__)
        #         for attr in init_hints:
        #             if attr == "return" or attr.startswith("_"):
        #                 continue

        #             alias = map_func(attr)
        #             if alias != attr:
        #                 reversed_mappings[alias] = attr

        def custom_setattr(self, name: str, value: Any) -> None:
            if name in reversed_mappings:
                original_setattr(self, reversed_mappings[name], value)
            else:
                original_setattr(self, name, value)

        def custom_getattribute(self, name: str) -> Any:
            if name in reversed_mappings:
                return original_getattribute(self, reversed_mappings[name])
            else:
                return original_getattribute(self, name)

        cls.__getattribute__ = custom_getattribute
        cls.__setattr__ = custom_setattr

        return cls

    return decorator


def parameter_aliases(mappings: Dict[str, str]):
    def decorator(func):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        reversed_mappings = {alias: param for param, alias in mappings.items()}

        for i, p in enumerate(params):
            if p.name in mappings:
                params[i] = p.replace(name=mappings[p.name])

        new_sig = sig.replace(parameters=params)

        @wraps(func)
        def wrapper(*args, **kwargs):
            alias_kwargs = {}
            for alias, value in kwargs.items():
                if alias in reversed_mappings:
                    alias_kwargs[reversed_mappings[alias]] = value
                else:
                    alias_kwargs[alias] = value
            return func(*args, **alias_kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            alias_kwargs = {}
            for alias, value in kwargs.items():
                if alias in reversed_mappings:
                    alias_kwargs[reversed_mappings[alias]] = value
                else:
                    alias_kwargs[alias] = value
            return await func(*args, **alias_kwargs)

        if inspect.iscoroutinefunction(func):
            async_wrapper.__signature__ = new_sig
            return async_wrapper

        wrapper.__signature__ = new_sig
        return wrapper

    return decorator


def exclude_docstring(target: Any):
    return target


def exclude_coroutine(func: Callable):
    return func
