import inspect
from functools import wraps
from typing import Callable, get_type_hints

from pydantic import ConfigDict, TypeAdapter

from chat2edit.execution.exceptions import FeedbackException
from chat2edit.models import Feedback
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator
from chat2edit.utils import anno_repr


@exclude_this_decorator
def feedback_invalid_parameter_type(func: Callable):
    def validate_args(*args, **kwargs) -> None:
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        hints = get_type_hints(func)

        for param_name, param_value in bound_args.arguments.items():
            param_anno = hints.get(param_name)

            if not param_anno:
                continue

            try:
                config = ConfigDict(arbitrary_types_allowed=True)
                adaptor = TypeAdapter(param_anno, config=config)
            except:  # noqa: E722
                adaptor = TypeAdapter(param_anno)

            try:
                adaptor.validate_python(param_value)
            except:  # noqa: E722
                feedback = Feedback(
                    type="invalid_parameter_type",
                    severity="error",
                    function=func.__name__,
                    details={
                        "parameter": param_name,
                        "expected_type": anno_repr(param_anno),
                        "received_type": type(param_value).__name__,
                    },
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
