import inspect
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, get_type_hints

from chat2edit.prompting.stubbing.constants import (
    ATTRIBUTE_MAP_FUNCTION_KEY,
    ATTRIBUTE_TO_ALIAS_KEY,
    BASE_TO_ALIAS_KEY,
    COROUTINE_EXCLUDED_KEY,
    DOCSTRING_EXCLUDED_KEY,
    EXCLUDED_ATTRIBUTES_KEY,
    EXCLUDED_BASES_KEY,
    EXCLUDED_DECORATORS_KEY,
    EXCLUDED_METHODS_KEY,
    INCLUDED_ATTRIBUTES_KEY,
    INCLUDED_BASES_KEY,
    INCLUDED_DECORATORS_KEY,
    INCLUDED_METHODS_KEY,
    METHOD_MAP_FUNCTION_KEY,
    METHOD_TO_ALIAS_KEY,
    PARAMETER_TO_ALIAS_KEY,
)
from chat2edit.prompting.stubbing.utils import (
    append_list_attr,
    extend_list_attr,
    update_dict_attr,
)


def exclude_this_decorator(decorator: Callable):
    @wraps(decorator)
    def wrapper(target):
        append_list_attr(target, EXCLUDED_DECORATORS_KEY, decorator.__name__)
        return decorator(target)

    return wrapper


def exclude_this_decorator_factory(factory: Callable):
    @wraps(factory)
    def wrapper(*args, **kwargs):
        def factory_wrapper(target):
            append_list_attr(target, EXCLUDED_DECORATORS_KEY, factory.__name__)
            return factory(*args, **kwargs)(target)

        return factory_wrapper

    return wrapper


@exclude_this_decorator_factory
def alias(alias: str):
    def decorator(target):
        target.__name__ = alias
        return target

    return decorator


@exclude_this_decorator_factory
def include_decorators(decorators: List[str]):
    def decorator(target):
        extend_list_attr(target, INCLUDED_DECORATORS_KEY, decorators)
        return target

    return decorator


@exclude_this_decorator_factory
def exclude_decorators(decorators: List[str]):
    def decorator(target):
        extend_list_attr(target, EXCLUDED_DECORATORS_KEY, decorators)
        return target

    return decorator


@exclude_this_decorator_factory
def include_bases(bases: List[str]):
    def decorator(cls):
        extend_list_attr(cls, INCLUDED_BASES_KEY, bases)
        return cls

    return decorator


@exclude_this_decorator_factory
def exclude_bases(bases: List[str]):
    def decorator(cls):
        extend_list_attr(cls, EXCLUDED_BASES_KEY, bases)
        return cls

    return decorator


@exclude_this_decorator_factory
def include_attributes(attributes: List[str]):
    def decorator(cls):
        extend_list_attr(cls, INCLUDED_ATTRIBUTES_KEY, attributes)
        return cls

    return decorator


@exclude_this_decorator_factory
def exclude_attributes(attributes: List[str]):
    def decorator(cls):
        extend_list_attr(cls, EXCLUDED_ATTRIBUTES_KEY, attributes)
        return cls

    return decorator


@exclude_this_decorator_factory
def include_methods(methods: List[str]):
    def decorator(cls):
        extend_list_attr(cls, INCLUDED_METHODS_KEY, methods)
        return cls

    return decorator


@exclude_this_decorator_factory
def exclude_methods(methods: List[str]):
    def decorator(cls):
        extend_list_attr(cls, EXCLUDED_METHODS_KEY, methods)
        return cls

    return decorator


@exclude_this_decorator_factory
def base_aliases(param_to_alias: Dict[str, str]):
    def decorator(cls):
        update_dict_attr(cls, BASE_TO_ALIAS_KEY, param_to_alias)
        return cls

    return decorator


@exclude_this_decorator_factory
def attribute_aliases(
    attr_to_alias: Dict[str, str], map_func: Optional[Callable[[str], str]] = None
):
    alias_to_attr = {v: k for k, v in attr_to_alias.items()}

    def decorator(cls):
        update_dict_attr(cls, ATTRIBUTE_TO_ALIAS_KEY, attr_to_alias)
        setattr(cls, ATTRIBUTE_MAP_FUNCTION_KEY, map_func)

        original_getattribute = cls.__getattribute__
        original_setattr = cls.__setattr__

        if map_func:
            hints = get_type_hints(cls)
            for attr in hints:
                if attr.startswith("_"):
                    continue

                alias = map_func(attr)
                if alias != attr:
                    alias_to_attr[alias] = attr

            if hasattr(cls, "__init__"):
                init_hints = get_type_hints(cls.__init__)
                for attr in init_hints:
                    if attr == "return" or attr.startswith("_"):
                        continue

                    alias = map_func(attr)
                    if alias != attr:
                        alias_to_attr[alias] = attr

        def custom_setattr(self, name: str, value) -> None:
            original_setattr(self, alias_to_attr.get(name, name), value)

        def custom_getattribute(self, name: str) -> Any:
            return original_getattribute(self, alias_to_attr.get(name, name))

        cls.__getattribute__ = custom_getattribute
        cls.__setattr__ = custom_setattr

        return cls

    return decorator


@exclude_this_decorator_factory
def method_aliases(
    attr_to_alias: Dict[str, str], map_func: Optional[Callable[[str], str]] = None
):
    alias_to_attr = {v: k for k, v in attr_to_alias.items()}

    def decorator(cls):
        update_dict_attr(cls, METHOD_TO_ALIAS_KEY, attr_to_alias)
        setattr(cls, METHOD_MAP_FUNCTION_KEY, map_func)

        original_getattribute = cls.__getattribute__
        original_setattr = cls.__setattr__

        if map_func:
            hints = get_type_hints(cls)
            for attr in hints:
                if attr.startswith("_"):
                    continue

                alias = map_func(attr)
                if alias != attr:
                    alias_to_attr[alias] = attr

            if hasattr(cls, "__init__"):
                init_hints = get_type_hints(cls.__init__)
                for attr in init_hints:
                    if attr == "return" or attr.startswith("_"):
                        continue

                    alias = map_func(attr)
                    if alias != attr:
                        alias_to_attr[alias] = attr

        def custom_setattr(self, name: str, value) -> None:
            original_setattr(self, alias_to_attr.get(name, name), value)

        def custom_getattribute(self, name: str) -> Any:
            return original_getattribute(self, alias_to_attr.get(name, name))

        cls.__getattribute__ = custom_getattribute
        cls.__setattr__ = custom_setattr

        return cls

    return decorator


@exclude_this_decorator_factory
def parameter_aliases(param_to_alias: Dict[str, str]):
    def decorator(func):
        update_dict_attr(func, PARAMETER_TO_ALIAS_KEY, param_to_alias)

        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        alias_to_param = {v: k for k, v in param_to_alias.items()}

        for i, p in enumerate(params):
            if p.name in param_to_alias:
                params[i] = p.replace(name=param_to_alias[p.name])

        new_sig = sig.replace(parameters=params)

        @wraps(func)
        def wrapper(*args, **kwargs):
            alias_kwargs = {}
            for k, v in kwargs.items():
                alias_kwargs[alias_to_param.get(k, k)] = v

            return func(*args, **alias_kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            alias_kwargs = {}
            for k, v in kwargs.items():
                alias_kwargs[alias_to_param.get(k, k)] = v

            return await func(*args, **alias_kwargs)

        if inspect.iscoroutinefunction(func):
            async_wrapper.__signature__ = new_sig
            return async_wrapper

        wrapper.__signature__ = new_sig
        return wrapper

    return decorator


@exclude_this_decorator
def exclude_docstring(target: Any) -> Any:
    setattr(target, DOCSTRING_EXCLUDED_KEY, True)
    return target


@exclude_this_decorator
def exclude_coroutine(func: Callable) -> Callable:
    setattr(func, COROUTINE_EXCLUDED_KEY, True)
    return func
