import ast
import keyword
from typing import Dict

import astor
import black


class CodeReplacer(ast.NodeTransformer):
    def __init__(self, mappings: Dict[str, str]):
        self.mappings = mappings

    @classmethod
    def replace(cls, code: str, mappings: Dict[str, str]):
        tree = ast.parse(code)

        transformer = cls(mappings)
        transformed_tree = transformer.visit(tree)

        transformed_code = astor.to_source(transformed_tree)
        format_mode = black.Mode(line_length=1000, is_pyi=True)
        formatted_code = black.format_str(transformed_code, mode=format_mode)

        return formatted_code


class NameReplacer(CodeReplacer):
    def visit_Name(self, node: ast.Name):
        if not keyword.iskeyword(node.id) and node.id not in {"self", "cls"}:
            node.id = self.mappings.get(node.id, node.id)

        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        node.name = self.mappings.get(node.name, node.name)

        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.name = self.mappings.get(node.name, node.name)

        for arg in node.args.args:
            arg.arg = self.mappings.get(arg.arg, arg.arg)

        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        node.name = self.mappings.get(node.name, node.name)

        for arg in node.args.args:
            arg.arg = self.mappings.get(arg.arg, arg.arg)

        return node


class AttributeReplacer(CodeReplacer):
    def visit_Assign(self, node: ast.Assign):
        for i, target in enumerate(node.targets):
            unparsed_target = ast.unparse(target)

            if unparsed_target in self.mappings:
                node.targets[i] = ast.parse(self.mappings[unparsed_target])

        return node

    def visit_AnnAssign(self, node: ast.AnnAssign):
        unparsed_target = ast.unparse(node.target)

        if unparsed_target in self.mappings:
            node.target = ast.parse(self.mappings[unparsed_target])

        return node


class ParameterReplacer(CodeReplacer):
    def __init__(self, mappings: Dict[str, str]):
        self.mappings = mappings

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for arg in node.args.args:
            arg.arg = self.mappings.get(arg.arg, arg.arg)

        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        for arg in node.args.args:
            arg.arg = self.mappings.get(arg.arg, arg.arg)

        return node
