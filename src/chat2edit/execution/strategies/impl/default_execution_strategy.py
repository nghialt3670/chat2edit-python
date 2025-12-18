import ast
import re
import textwrap
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, Tuple

from IPython.core.interactiveshell import InteractiveShell

from chat2edit.execution.exceptions import FeedbackException, ResponseException
from chat2edit.execution.signaling import pop_feedback, pop_response
from chat2edit.execution.strategies.execution_strategy import ExecutionStrategy
from chat2edit.execution.utils import fix_unawaited_async_calls
from chat2edit.models import ExecutionError, Feedback, Message


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    # Pattern to match ANSI escape sequences
    # Matches: \x1b[...m or \033[...m or \x1b[K (clear line) etc.
    ansi_escape = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\[K|\033\[[0-9;]*[a-zA-Z]|\033\[K")
    return ansi_escape.sub("", text)


class DefaultExecutionStrategy(ExecutionStrategy):
    def parse(self, code: str) -> List[str]:
        dedented_code = textwrap.dedent(code)
        tree = ast.parse(dedented_code)
        return [ast.unparse(node).strip() for node in tree.body]

    def process(self, code: str, context: Dict[str, Any]) -> str:
        return fix_unawaited_async_calls(code, context)

    async def execute(
        self,
        code: str,
        context: Dict[str, Any],
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Tuple[
        Optional[ExecutionError],
        Optional[Feedback],
        Optional[Message],
        List[str],
    ]:
        error: Optional[ExecutionError] = None
        feedback: Optional[Feedback] = None
        response: Optional[Message] = None
        logs: List[str] = []

        InteractiveShell.clear_instance()

        shell = InteractiveShell.instance()
        shell.cleanup()

        shell.user_ns.update(context)
        keys = set(shell.user_ns.keys())

        class _LogStream:
            def __init__(self, on_log_cb: Optional[Callable[[str], None]]) -> None:
                self._buffer = StringIO()
                self._on_log = on_log_cb
                self._line_buffer = ""

            def write(self, s: str) -> int:
                self._buffer.write(s)
                if self._on_log and s:
                    text = strip_ansi_codes(s)
                    self._line_buffer += text
                    while "\n" in self._line_buffer:
                        line, self._line_buffer = self._line_buffer.split("\n", 1)
                        if line:
                            self._on_log(line)
                return len(s)

            def flush(self) -> None:
                self._buffer.flush()

            def getvalue(self) -> str:
                return strip_ansi_codes(self._buffer.getvalue())

        log_buffer = _LogStream(on_log)

        try:
            with redirect_stdout(log_buffer), redirect_stderr(log_buffer):
                result = await shell.run_cell_async(code, silent=True)

        finally:
            new_keys = set(shell.user_ns.keys()).difference(keys)
            context.update({k: v for k, v in shell.user_ns.items() if k in new_keys})

        try:
            result.raise_error()
        except FeedbackException as e:
            feedback = e.feedback
        except ResponseException as e:
            response = e.response
        except Exception as e:
            execution_error = ExecutionError.from_exception(e)
            error = execution_error
            feedback = Feedback(
                type="unexpected_error",
                severity="error",
                details={
                    "error": execution_error.model_dump(),
                },
            )
        finally:
            log_text = log_buffer.getvalue()
            logs = [line for line in log_text.splitlines() if line]

        feedback = feedback or pop_feedback()
        response = response or pop_response()

        return error, feedback, response, logs
