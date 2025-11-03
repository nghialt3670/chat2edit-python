import inspect
from functools import wraps
from typing import Callable, List

from chat2edit.execution.exceptions import FeedbackException
from chat2edit.execution.feedbacks import EmptyListParametersFeedback
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator_factory


@exclude_this_decorator_factory
def feedback_empty_list_parameters(parameters: List[str]) -> Callable:
    def decorator(func: Callable) -> Callable:
        def validate_lists_not_empty(*args, **kwargs) -> None:
            signature = inspect.signature(func)
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Get the parameter values and check for empty lists
            empty_params = []

            for param_name in parameters:
                param_value = bound_args.arguments.get(param_name)

                if param_value is None:
                    continue  # Skip validation if parameter is not provided

                # Check if it's a list/sequence
                if not hasattr(param_value, "__len__"):
                    continue  # Skip validation if parameter is not a sequence

                # Check if empty
                if len(param_value) == 0:
                    empty_params.append(param_name)

            # If any parameters are empty, raise feedback
            if empty_params:
                feedback = EmptyListParametersFeedback(
                    severity="error",
                    function=func.__name__,
                    parameters=empty_params,
                )
                raise FeedbackException(feedback)

        @wraps(func)
        def wrapper(*args, **kwargs):
            validate_lists_not_empty(*args, **kwargs)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            validate_lists_not_empty(*args, **kwargs)
            return await func(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper

    return decorator
