import inspect
from functools import wraps
from typing import Callable, List

from chat2edit.execution.exceptions import FeedbackException
from chat2edit.models import Feedback
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator_factory


@exclude_this_decorator_factory
def feedback_mismatch_list_parameters(parameters: List[str]) -> Callable:
    def decorator(func: Callable) -> Callable:
        def validate_list_lengths(*args, **kwargs) -> None:
            signature = inspect.signature(func)
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Get the parameter values and their lengths
            param_values = []
            param_lengths = []
            valid_params = []

            for param_name in parameters:
                param_value = bound_args.arguments.get(param_name)

                if param_value is None:
                    continue  # Skip validation if parameter is not provided

                # Check if it's a list/sequence
                if not hasattr(param_value, "__len__"):
                    continue  # Skip validation if parameter is not a sequence

                param_values.append(param_value)
                param_lengths.append(len(param_value))
                valid_params.append(param_name)

            # If we have less than 2 valid parameters, skip validation
            if len(valid_params) < 2:
                return

            # Check if all lengths are the same
            first_length = param_lengths[0]
            if not all(length == first_length for length in param_lengths):
                feedback = Feedback(
                    type="mismatch_list_parameters",
                    severity="error",
                    function=func.__name__,
                    details={
                        "parameters": valid_params,
                        "lengths": param_lengths,
                    },
                )
                raise FeedbackException(feedback)

        @wraps(func)
        def wrapper(*args, **kwargs):
            validate_list_lengths(*args, **kwargs)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            validate_list_lengths(*args, **kwargs)
            return await func(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper

    return decorator
