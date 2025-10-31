import inspect
from functools import wraps
from typing import Callable

from chat2edit.execution.signaling import set_response
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator


@exclude_this_decorator
def respond(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        set_response(response)
        return response

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        response = await func(*args, **kwargs)
        set_response(response)
        return response

    return async_wrapper if inspect.iscoroutinefunction(func) else wrapper
