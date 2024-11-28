import ast
import inspect
import io
from contextlib import redirect_stdout
from typing import Any, Dict

from IPython.core.interactiveshell import InteractiveShell

from chat2edit.base import ContextProvider
from chat2edit.context import contextualize_message, decontextualize_message
from chat2edit.exceptions import FeedbackException
from chat2edit.feedbacks import (
    FunctionMessageFeedback,
    IncompleteCycleFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.models import Error, ExecutionResult
from chat2edit.signaling import (
    clear_feedback,
    clear_response,
    get_feedback,
    get_response,
)
from chat2edit.utils.code import fix_unawaited_async_calls


async def execute(
    code: str, exec_context: Dict[str, Any], provider: ContextProvider
) -> ExecutionResult:
    shell = InteractiveShell.instance()
    exec_context.update(shell.user_ns)
    shell.user_ns = exec_context

    result = ExecutionResult()

    try:
        tree = ast.parse(code)
    except Exception as e:
        result.error = Error.from_exception(e)
        return result

    async_func_names = [
        k for k, v in exec_context.items() if inspect.iscoroutinefunction(v)
    ]

    for node in tree.body:
        block = ast.unparse(node)
        result.blocks.append(block)

        fixed_block = fix_unawaited_async_calls(block, async_func_names)

        try:
            with io.StringIO() as buffer, redirect_stdout(buffer):
                cell_result = await shell.run_cell_async(fixed_block, silent=True)
                cell_result.raise_error()

        except FeedbackException as e:
            result.feedback = e.feedback

            break

        except Exception as e:
            error = Error.from_exception(e)
            result.feedback = UnexpectedErrorFeedback(error=error)
            break

        if response := get_response():
            result.response = contextualize_message(response, exec_context, provider)
            break

        if feedback := get_feedback():
            if isinstance(feedback, FunctionMessageFeedback):
                result.feedback = decontextualize_message(feedback, exec_context)
            else:
                result.feedback = feedback

            break

    clear_feedback()
    clear_response()

    if not (result.response or result.feedback):
        result.feedback = IncompleteCycleFeedback()

    return result
