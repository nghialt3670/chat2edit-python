import inspect
from functools import wraps
from typing import Callable

from chat2edit.execution.exceptions import FeedbackException
from chat2edit.execution.feedbacks import UnexpectedErrorFeedback
from chat2edit.models import ExecutionError
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator


@exclude_this_decorator
def feedback_unexpected_error(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FeedbackException as e:
            raise e
        except Exception as e:
            error = ExecutionError.from_exception(e)
            error.function = func.__name__
            feedback = UnexpectedErrorFeedback(error=error)
            raise FeedbackException(feedback)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FeedbackException as e:
            raise e
        except Exception as e:
            error = ExecutionError.from_exception(e)
            error.function = func.__name__
            feedback = UnexpectedErrorFeedback(error=error)
            raise FeedbackException(feedback)

    return async_wrapper if inspect.iscoroutinefunction(func) else wrapper
