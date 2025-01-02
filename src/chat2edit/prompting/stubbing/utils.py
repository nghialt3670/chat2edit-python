import ast
import inspect
import re
import sys
import textwrap
from itertools import chain
from typing import Any, Dict, Iterable


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


def extend_list_attr(target: Any, attr: str, values: Iterable[Any]) -> None:
    setattr(target, attr, list(chain(getattr(target, attr, []), values)))


def append_list_attr(target: Any, attr: str, value: Any) -> None:
    extend_list_attr(target, attr, [value])


def update_dict_attr(target: Any, attr: str, update: Dict) -> None:
    d = getattr(target, attr, {})
    d.update(update)
    setattr(target, attr, d)
