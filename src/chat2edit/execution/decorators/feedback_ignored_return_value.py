import inspect
from functools import wraps
from typing import Callable, get_type_hints

from chat2edit.execution.exceptions import FeedbackException
from chat2edit.execution.feedbacks import IgnoredReturnValueFeedback
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator
from chat2edit.utils import anno_repr


@exclude_this_decorator
def feedback_ignored_return_value(func: Callable):
    def check_caller_frame() -> None:
        current_frame = inspect.currentframe()
        if not current_frame or not current_frame.f_back or not current_frame.f_back.f_back:
            return
        caller_frame = current_frame.f_back.f_back
        instructions = list(inspect.getframeinfo(caller_frame).code_context or [])

        if not any(" = " in line for line in instructions):
            feedback = IgnoredReturnValueFeedback(
                function=func.__name__,
                value_type=anno_repr(get_type_hints(func).get("return")),
            )
            raise FeedbackException(feedback)

    @wraps(func)
    def wrapper(*args, **kwargs):
        check_caller_frame()
        return func(*args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        check_caller_frame()
        return await func(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(func) else wrapper
