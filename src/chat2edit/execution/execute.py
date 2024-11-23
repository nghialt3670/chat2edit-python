import ast
import inspect
import io
from contextlib import redirect_stdout
from typing import Any, Dict

from IPython.core.interactiveshell import InteractiveShell

from chat2edit.execution.exceptions import FeedbackException, FileObjModifiedException
from chat2edit.execution.helpers import fix_unawaited_async_calls
from chat2edit.execution.signaling import SignalManager
from chat2edit.models.cobject import FileObjModifiedError
from chat2edit.models.cycles import ExecutionResult
from chat2edit.models.error import Error
from chat2edit.models.execution import (
    FunctionMessageFeedback,
    IncompleteCycleFeedback,
    UnexpectedErrorFeedback,
)


async def execute(code: str, context: Dict[str, Any]) -> ExecutionResult:
    shell = InteractiveShell.instance()
    context.update(shell.user_ns)
    shell.user_ns = context

    result = ExecutionResult()

    try:
        tree = ast.parse(code)
    except Exception as e:
        result.error = Error.from_exception(e)
        return result

    async_func_names = [k for k, v in context.items() if inspect.iscoroutinefunction(v)]

    for node in tree.body:
        block = ast.unparse(node)
        result.blocks.append(block)

        fixed_block = fix_unawaited_async_calls(block, async_func_names)

        try:
            with io.StringIO() as buffer, redirect_stdout(buffer):
                cell_result = await shell.run_cell_async(fixed_block, silent=True)
                cell_result.raise_error()

        except FileObjModifiedError as e:
            raise FileObjModifiedException(e.varname, e.member)

        except FeedbackException as e:
            result.feedback = e.get_feedback()

            if isinstance(result.feedback, FunctionMessageFeedback):
                result.feedback.convert_objs_to_paths(shell.user_ns)

            break

        except Exception as e:
            error = Error.from_exception(e)
            result.feedback = UnexpectedErrorFeedback(severity="error", error=error)
            break

        if SignalManager.check_response():
            result.response = SignalManager.get_response()
            result.response.convert_objs_to_paths(shell.user_ns)
            break

        if SignalManager.check_feedback():
            result.feedback = SignalManager.get_feedback()
            break

    SignalManager.clear_signals()

    if not (result.response or result.feedback):
        result.feedback = IncompleteCycleFeedback(severity="info")

    return result
