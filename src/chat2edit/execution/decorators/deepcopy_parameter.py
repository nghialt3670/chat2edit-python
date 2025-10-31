import inspect
from copy import deepcopy
from functools import wraps
from typing import Callable

from chat2edit.prompting.stubbing.decorators import exclude_this_decorator_factory


@exclude_this_decorator_factory
def deepcopy_parameter(param: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        def check_and_transform_args_kwargs(args, kwargs):
            params = func.__code__.co_varnames[: func.__code__.co_argcount]

            if param in params:
                index = params.index(param)
                if index < len(args):
                    args = tuple(
                        deepcopy(arg) if i == index else arg
                        for i, arg in enumerate(args)
                    )

            if param in kwargs:
                kwargs[param] = deepcopy(kwargs[param])

            return args, kwargs

        @wraps(func)
        def wrapper(*args, **kwargs):
            args, kwargs = check_and_transform_args_kwargs(args, kwargs)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            args, kwargs = check_and_transform_args_kwargs(args, kwargs)
            return await func(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper

    return decorator
