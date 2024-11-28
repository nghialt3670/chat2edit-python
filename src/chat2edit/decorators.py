import inspect
from functools import wraps
from typing import Any, Callable, List, Type

from chat2edit.constants import CLASS_INFO_EXCLUDES_KEY, PYDANTIC_MODEL_EXCLUDES
from chat2edit.exceptions import FeedbackException
from chat2edit.feedbacks import (
    InvalidArgumentFeedback,
    Parameter,
    UnassignedValueFeedback,
)
from chat2edit.models import Error
from chat2edit.utils.repr import anno_repr
from chat2edit.utils.typing import validate_type


def feedback_invalid_argument(func: Callable):
    def validate_args(*args, **kwargs) -> None:
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for param_name, param_value in bound_args.arguments.items():
            param_anno = signature.parameters[param_name].annotation

            if param_anno is inspect.Signature.empty:
                continue

            if not validate_type(param_value, param_anno):
                feedback = InvalidArgumentFeedback(
                    param=Parameter(
                        name=param_name,
                        anno=anno_repr(param_anno),
                        type=type(param_value).__name__,
                    )
                )
                raise FeedbackException(feedback)

    @wraps(func)
    def wrapper(*args, **kwargs):
        validate_args(*args, **kwargs)
        return func(*args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        validate_args(*args, **kwargs)
        return await func(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(func) else wrapper


def feedback_unassigned_value(func: Callable):
    def check_caller_frame() -> None:
        caller_frame = inspect.currentframe().f_back.f_back
        instructions = list(inspect.getframeinfo(caller_frame).code_context or [])

        if not any(" = " in line for line in instructions):
            feedback = UnassignedValueFeedback(
                severity="error",
                func=func.__name__,
                rtype=anno_repr(func.__annotations__.get("return", None)),
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


def feedback_unexpected_error(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FeedbackException as e:
            raise e
        except Exception as e:
            error = Error.from_exception(e)
            raise FeedbackException(error)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FeedbackException as e:
            raise e
        except Exception as e:
            error = Error.from_exception(e)
            raise FeedbackException(error)

    return async_wrapper if inspect.iscoroutinefunction(func) else wrapper


def exclude(excludes: List[str]):
    def decorator(cls: Type[Any]):
        setattr(cls, CLASS_INFO_EXCLUDES_KEY, excludes)
        return cls

    return decorator


pydantic_exclude = exclude(PYDANTIC_MODEL_EXCLUDES)
