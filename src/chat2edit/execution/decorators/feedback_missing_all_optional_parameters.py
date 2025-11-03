import inspect
from functools import wraps
from typing import Callable, List

from chat2edit.execution.exceptions import FeedbackException
from chat2edit.execution.feedbacks import MissingAllOptionalParametersFeedback
from chat2edit.prompting.stubbing.decorators import exclude_this_decorator_factory


@exclude_this_decorator_factory
def feedback_missing_all_optional_parameters(parameters: List[str]) -> Callable:
    def decorator(func: Callable) -> Callable:
        def validate_at_least_one_param(*args, **kwargs) -> None:
            signature = inspect.signature(func)
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Check if at least one parameter is provided (not None)
            provided_params = []
            for param_name in parameters:
                param_value = bound_args.arguments.get(param_name)
                if param_value is not None:
                    provided_params.append(param_name)

            # If no parameters are provided, raise feedback
            if not provided_params:
                feedback = MissingAllOptionalParametersFeedback(
                    severity="error",
                    function=func.__name__,
                    parameters=parameters,
                )
                raise FeedbackException(feedback)

        @wraps(func)
        def wrapper(*args, **kwargs):
            validate_at_least_one_param(*args, **kwargs)
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            validate_at_least_one_param(*args, **kwargs)
            return await func(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper

    return decorator
