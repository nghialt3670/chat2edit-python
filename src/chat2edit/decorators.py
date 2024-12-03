import inspect
from functools import wraps
from typing import Any, Callable, Iterable, List, Type

from pydantic import ConfigDict, TypeAdapter

from chat2edit.constants import CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY
from chat2edit.exceptions import FeedbackException
from chat2edit.feedbacks import (
    InvalidArgumentFeedback,
    Parameter,
    UnassignedValueFeedback,
)
from chat2edit.models import Error
from chat2edit.signaling import set_response
from chat2edit.stubbing.decorators import *
from chat2edit.utils.repr import anno_repr


def feedback_invalid_argument(func: Callable):
    def validate_args(*args, **kwargs) -> None:
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for param_name, param_value in bound_args.arguments.items():
            param_anno = signature.parameters[param_name].annotation

            if param_anno is inspect.Signature.empty:
                continue

            try:
                config = ConfigDict(arbitrary_types_allowed=True)
                adaptor = TypeAdapter(param_anno, config=config)
                adaptor.validate_python(param_value)
            except:
                feedback = InvalidArgumentFeedback(
                    func=func.__name__,
                    param=Parameter(
                        name=param_name,
                        anno=anno_repr(param_anno),
                        type=type(param_value).__name__,
                    ),
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

    ret_wrapper = async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    extend_excluded_decorators(ret_wrapper, ["feedback_invalid_argument"])
    return ret_wrapper


def feedback_unassigned_value(func: Callable):
    def check_caller_frame() -> None:
        caller_frame = inspect.currentframe().f_back.f_back
        instructions = list(inspect.getframeinfo(caller_frame).code_context or [])

        if not any(" = " in line for line in instructions):
            feedback = UnassignedValueFeedback(
                severity="error",
                func=func.__name__,
                anno=anno_repr(func.__annotations__.get("return", None)),
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

    ret_wrapper = async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    extend_excluded_decorators(ret_wrapper, ["feedback_unassigned_value"])
    return ret_wrapper


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

    ret_wrapper = async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    extend_excluded_decorators(ret_wrapper, ["feedback_unexpected_error"])
    return ret_wrapper


def response(func: Callable):
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

    ret_wrapper = async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    extend_excluded_decorators(ret_wrapper, ["response"])
    return ret_wrapper
