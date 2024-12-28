import ast
from typing import Any, get_args

from chat2edit.prompting.stubbing.stubs import (
    AssignInfo,
    AssignNodeType,
    ClassStub,
    CodeStub,
    FunctionNodeType,
    FunctionStub,
    ImportInfo,
    ImportNodeType,
)


class ClassStubBuilder(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.stub = None

    def build(self, node: ast.ClassDef) -> ClassStub:
        self.stub = ClassStub(
            name=node.name,
            bases=list(map(ast.unparse, node.bases)),
            decorators=list(map(ast.unparse, node.decorator_list)),
        )
        self.visit(node)
        return self.stub

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.ClassDef):
            return super().visit(node)

        elif isinstance(node, get_args(AssignNodeType)):
            self.stub.attributes.append(AssignInfo.from_node(node))

        elif isinstance(node, get_args(FunctionNodeType)):
            self.stub.methods.append(FunctionStub.from_node(node))


class CodeStubBuilder(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.stub = None

    def build(self, node: ast.Module) -> "ClassStub":
        self.stub = CodeStub()
        self.visit(node)
        return self.stub

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Module):
            return super().visit(node)

        if isinstance(node, get_args(ImportNodeType)):
            self.stub.blocks.append(ImportInfo.from_node(node))

        elif isinstance(node, ast.ClassDef):
            self.stub.blocks.append(ClassStub.from_node(node))

        elif isinstance(node, get_args(FunctionNodeType)):
            self.stub.blocks.append(FunctionStub.from_node(node))

        elif isinstance(node, get_args(AssignNodeType)):
            self.stub.blocks.append(AssignInfo.from_node(node))
