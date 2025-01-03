from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Dict

from IPython.core.interactiveshell import InteractiveShell

from chat2edit.execution.utils import fix_unawaited_async_calls


def process_code(code: str, context: Dict[str, Any]) -> str:
    return fix_unawaited_async_calls(code, context)


async def execute_code(code: str, context: Dict[str, Any]) -> None:
    shell = InteractiveShell.instance()

    shell.user_ns.update(context)
    keys = set(shell.user_ns.keys())

    out_buffer = StringIO()
    err_buffer = StringIO()

    try:
        with redirect_stdout(out_buffer), redirect_stderr(err_buffer):
            result = await shell.run_cell_async(code, silent=True)

    finally:
        new_keys = set(shell.user_ns.keys()).difference(keys)
        context.update({k: v for k, v in shell.user_ns.items() if k in new_keys})
        result.raise_error()
