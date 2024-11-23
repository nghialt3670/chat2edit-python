import ast
from typing import List, Set

import astor


class AsyncCallCorrector(ast.NodeTransformer):
    def __init__(self, async_func_names: Set[str]):
        super().__init__()
        self.async_func_names = async_func_names

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.async_func_names:
                if not isinstance(getattr(node, "parent", None), ast.Await):
                    return ast.Await(value=node)

        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function_is_async = (
            node.args.kwonlyargs is not None and isinstance(node, ast.AsyncFunctionDef)
        )
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.current_function_is_async = True
        self.generic_visit(node)
        return node


def add_parent_info(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        child.parent = node
        add_parent_info(child)


def fix_unawaited_async_calls(code: str, async_func_names: List[str]) -> str:
    tree = ast.parse(code)
    add_parent_info(tree)

    transformer = AsyncCallCorrector(set(async_func_names))
    fixed_tree = transformer.visit(tree)

    ast.fix_missing_locations(fixed_tree)
    fixed_code = astor.to_source(fixed_tree)

    return fixed_code
