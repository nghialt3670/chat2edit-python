import ast
import keyword
from typing import Dict, List, Set

import astor
import black

__all__ = ["fix_unawaited_async_calls"]


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
    formatted_code = black.format_str(fixed_code, mode=black.Mode(line_length=1000))

    return formatted_code


class NameTransformer(ast.NodeTransformer):
    def __init__(self, mappings: Dict[str, str]):
        self.mappings = mappings

    def visit_Name(self, node: ast.Name):
        if (not keyword.iskeyword(node.id) and node.id not in {"self", "cls"}) and node.id in self.mappings:
            node.id = self.mappings[node.id]
            
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name in self.mappings:
            node.name = self.mappings[node.name]
            
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name in self.mappings:
            node.name = self.mappings[node.name]
            
        self.generic_visit(node)
        return node


def replace_names(code: str, mappings: Dict[str, str]) -> str:
    tree = ast.parse(code)

    transformer = NameTransformer(mappings)
    transformed_tree = transformer.visit(tree)

    transformed_code = astor.to_source(transformed_tree)
    formatted_code = black.format_str(transformed_code, mode=black.Mode(line_length=1000))

    return formatted_code
