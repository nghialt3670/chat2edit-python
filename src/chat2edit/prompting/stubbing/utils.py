import ast
import inspect
import re
import sys
import textwrap
from typing import Any


def get_ast_node(target: Any) -> ast.AST:
    root = ast.walk(ast.parse(textwrap.dedent(inspect.getsource(target))))
    next(root)
    return next(root)


def get_node_doc(node: ast.AST) -> str:
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        return node.body[0].value.value

    return None


def get_call_args(call: str) -> str:
    return re.search(r"\((.*?)\)", call).group(1)


def is_external_package(obj: Any) -> bool:
    if inspect.isclass(obj) or inspect.isfunction(obj):
        module_name = obj.__module__
    else:
        try:
            module_name = obj.__class__.__module__
        except AttributeError:
            module_name = type(obj).__module__

    return not module_name.startswith(__name__.split(".")[0])


def find_shortest_import_path(obj: Any) -> str:
    candidates = []

    for name, module in list(sys.modules.items()):
        if module and getattr(module, obj.__name__, None) is obj:
            candidates.append(name)

    candidates = [c for c in candidates if not c.startswith("__")]
    return min(candidates, key=len)
