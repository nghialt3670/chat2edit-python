import inspect
from functools import wraps
from typing import Callable

from pydantic import TypeAdapter

from chat2edit.execution.exceptions import (
    FeedbackException,
    InvalidArgumentException,
    UnassignedValueException,
    UnexpectedErrorException,
)
from chat2edit.execution.signaling import SignalManager
from chat2edit.models.error import Error
from chat2edit.utils.repr import anno_repr


def feedback_invalid_argument(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for param_name, param_value in bound_args.arguments.items():
            param_anno = signature.parameters[param_name].annotation

            if param_anno is not inspect.Signature.empty:
                try:
                    TypeAdapter(param_anno).validate_python(param_value)
                except:
                    raise InvalidArgumentException(
                        func_name=func.__name__,
                        param_name=param_name,
                        param_anno=anno_repr(param_anno),
                        param_type=type(param_value).__name__,
                    )

        return func(*args, **kwargs)

    return wrapper


def feedback_unassigned_value(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        caller_frame = inspect.currentframe().f_back
        instructions = list(inspect.getframeinfo(caller_frame).code_context or [])

        if not any(" = " in line for line in instructions):
            func_name = func.__name__
            ret_anno = func.__annotations__.get("return", None)
            raise UnassignedValueException(func_name, anno_repr(ret_anno))

        return func(*args, **kwargs)

    return wrapper


def feedback_unexpected_error(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FeedbackException as e:
            raise e
        except Exception as e:
            error = Error.from_exception(e)
            raise UnexpectedErrorException(error)

    return wrapper


def response(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        SignalManager.signal_response(response)
        return response

    return wrapper
