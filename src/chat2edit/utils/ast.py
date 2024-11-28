import ast
import inspect
from typing import Any, Callable


def get_ast_node(target: Any) -> ast.AST:
    root = ast.walk(ast.parse(inspect.getsource(target)))
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
