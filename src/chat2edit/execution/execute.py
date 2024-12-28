import ast
import io
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from IPython.core.interactiveshell import InteractiveShell

from chat2edit.execution.exceptions import FeedbackException, ResponseException
from chat2edit.execution.feedbacks import (
    IncompleteCycleFeedback,
    UnexpectedErrorFeedback,
)
from chat2edit.execution.signaling import pop_feedback, pop_response
from chat2edit.execution.utils import fix_unawaited_async_calls
from chat2edit.models import Error, Feedback, Message


@dataclass
class ExecutionResult:
    blocks: List[str] = field(default_factory=list)
    feedback: Optional[Feedback] = field(default=None)
    response: Optional[Message] = field(default=None)
    error: Optional[Error] = field(default=None)


async def execute(
    *, code: str, context: str, on_block_execute: Optional[Callable[[str], None]] = None
) -> ExecutionResult:
    shell = InteractiveShell.instance()
    context.update(shell.user_ns)
    shell.user_ns = context

    result = ExecutionResult()

    try:
        tree = ast.parse(code)
    except Exception as e:
        result.error = Error.from_exception(e)
        return result

    for node in tree.body:
        block = ast.unparse(node)

        fixed_block = fix_unawaited_async_calls(block, context)
        result.blocks.append(fixed_block)

        if on_block_execute:
            on_block_execute(fixed_block)

        try:
            with io.StringIO() as buffer, redirect_stdout(buffer):
                cell_result = await shell.run_cell_async(fixed_block)
                cell_result.raise_error()

        except FeedbackException as e:
            result.feedback = e.feedback
            break

        except ResponseException as e:
            result.response = e.response
            break

        except Exception as e:
            error = Error.from_exception(e)
            result.feedback = UnexpectedErrorFeedback(error=error)
            break

        result.feedback = pop_feedback()
        result.response = pop_response()

        if result.feedback or result.response:
            break

    if not result.feedback and not result.response:
        result.feedback = IncompleteCycleFeedback()

    return result
