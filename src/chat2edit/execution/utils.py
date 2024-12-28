import ast
import inspect
from typing import Any, Dict

import astor
import black


class AsyncCallCorrector(ast.NodeTransformer):
    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        self.async_func_names = set(
            [k for k, v in context.items() if inspect.iscoroutinefunction(v)]
        )

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.async_func_names:
                if not isinstance(getattr(node, "parent", None), ast.Await):
                    return ast.Await(value=node)

        return self.generic_visit(node)


def add_parent_info(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        setattr(child, "parent", node)
        add_parent_info(child)


def fix_unawaited_async_calls(code: str, context: Dict[str, Any]) -> str:
    tree = ast.parse(code)
    add_parent_info(tree)

    transformer = AsyncCallCorrector(context)
    fixed_tree = transformer.visit(tree)

    ast.fix_missing_locations(fixed_tree)
    fixed_code = astor.to_source(fixed_tree)
    formatted_code = black.format_str(fixed_code, mode=black.Mode(line_length=1000))

    return formatted_code
