import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type, Union

from chat2edit.internal.exceptions import InvalidArgException
from chat2edit.utils.ast import get_ast_node, get_node_doc
from chat2edit.utils.repr import anno_repr

ImportNodeType = Union[ast.Import, ast.ImportFrom]

@dataclass
class ImportInfo:
    names: Tuple[str, Optional[str]]
    module: Optional[str] = field(default=None)

    @classmethod
    def from_node(cls, node: ImportNodeType) -> "ImportInfo":
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            raise InvalidArgException("node", ImportNodeType, node)

        names = [
            (name.name, ast.unparse(name.asname) if name.asname else None)
            for name in node.names
        ]

        if isinstance(node, ast.Import):
            return cls(names=names)

        return cls(names=names, module=node.module)

    @classmethod
    def from_obj(cls, obj: Any) -> "ImportInfo":
        obj_module = inspect.getmodule(obj)

        if obj_module == obj:
            return cls(names=[(obj.__name__, None)])

        return cls(names=[(obj.__name__, None)], module=obj_module.__name__)

    def __repr__(self) -> str:
        return f"{f'from {self.module} ' if self.module else ''}import {', '.join(map(lambda x: f'{x[0]} as {x[1]}' if x[1] else x[0], self.names))}"


AssignNodeType = Union[ast.Assign, ast.AnnAssign]


@dataclass
class AssignInfo:
    targets: List[str]
    value: Optional[str] = field(default=None)
    annotation: Optional[str] = field(default=None)

    @classmethod
    def from_node(cls, node: AssignNodeType) -> "AssignInfo":
        if isinstance(node, ast.Assign):
            return cls(
                targets=list(map(ast.unparse, node.targets)),
                value=ast.unparse(node.value),
            )

        if isinstance(node, ast.AnnAssign):
            return cls(
                targets=[ast.unparse(node.target)],
                value=ast.unparse(node.value) if node.value else None,
                annotation=ast.unparse(node.annotation),
            )

        raise InvalidArgException("node", AssignNodeType, node)

    @classmethod
    def from_param(cls, param: inspect.Parameter) -> "AssignInfo":
        return cls(
            target=param.name,
            value=(
                repr(param.default)
                if param.default is not inspect.Parameter.empty
                else None
            ),
            annotation=(
                anno_repr(param.annotation)
                if param.annotation is not inspect.Parameter.empty
                else None
            ),
        )

    def __repr__(self) -> str:
        value_repr = f" = {self.value}" if self.value else ""

        if self.annotation:
            return f"{self.targets[0]}: {self.annotation}{value_repr}"

        return f"{' = '.join(self.targets)}{value_repr}"


FunctionNodeType = Union[ast.FunctionDef, ast.AsyncFunctionDef]


@dataclass
class FunctionStub:
    name: str
    signature: str
    coroutine: bool = field(default=False)
    docstring: Optional[str] = field(default=None)
    decorators: List[str] = field(default_factory=list)

    @classmethod
    def from_node(cls, node: FunctionNodeType) -> "FunctionStub":
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise InvalidArgException("node", FunctionNodeType, node)

        signature = f"({ast.unparse(node.args)})"

        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"

        return cls(
            name=node.name,
            signature=signature,
            coroutine=isinstance(node, ast.AsyncFunctionDef),
            docstring=get_node_doc(node),
            decorators=list(map(ast.unparse, node.decorator_list)),
        )

    @classmethod
    def from_func(cls, func: Callable) -> "FunctionStub":
        node = get_ast_node(func)
        return cls.from_node(node)

    def __repr__(self) -> str:
        stub = ""

        if self.decorators:
            stub += "\n".join(f"@{dec}" for dec in self.decorators)
            stub += "\n"

        if self.coroutine:
            stub += "async "

        stub += f"def {self.name}{self.signature}: ..."

        return stub


ClassChildNodeType = Union[
    ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef
]


class ClassStubBuilder(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.stub = None
        self.excludes = None

    def build(self, node: ast.ClassDef, excludes: Iterable[str]) -> "ClassStub":
        self.stub = ClassStub(
            name=node.name,
            bases=list(map(ast.unparse, node.bases)),
            decorators=list(map(ast.unparse, node.decorator_list)),
        )
        self.excludes = set(excludes)
        self.visit(node)
        return self.stub

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.ClassDef):
            return super().visit(node)

        elif (
            isinstance(node, ast.Assign)
            and any(filter(self._check_name, map(ast.unparse, node.targets)))
        ) or (
            isinstance(node, ast.AnnAssign)
            and self._check_name(ast.unparse(node.target))
        ):
            self.stub.attributes.append(AssignInfo.from_node(node))

        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and self._check_name(node.name):
            self.stub.methods.append(FunctionStub.from_node(node))

    def _check_name(self, name: str) -> bool:
        return not (name in self.excludes or name.startswith("_"))


@dataclass
class ClassStub:
    name: str
    bases: List[str] = field(default_factory=list)
    attributes: List[AssignInfo] = field(default_factory=list)
    methods: List[FunctionStub] = field(default_factory=list)
    docstring: Optional[str] = field(default=None)
    decorators: List[str] = field(default_factory=list)

    @classmethod
    def from_node(cls, node: ast.ClassDef, excludes: Iterable[str] = []) -> "ClassStub":
        if not isinstance(node, ast.ClassDef):
            raise InvalidArgException("node", ast.ClassDef, node)

        return ClassStubBuilder().build(node, excludes)

    @classmethod
    def from_class(cls, clss: Type[Any], excludes: Iterable[str] = []) -> "ClassStub":
        node = get_ast_node(clss)
        return cls.from_node(node, excludes)

    def __repr__(self) -> str:
        stub = ""

        for dec in self.decorators:
            stub += f"@{dec}\n"

        stub += f"class {self.name}"

        if self.bases:
            stub += f"({', '.join(self.bases)})"

        stub += ":\n"

        if not self.attributes and not self.methods:
            stub += "    pass"
            return stub

        if self.attributes:
            stub += textwrap.indent("\n".join(map(str, self.attributes)), "    ")
            stub += "\n"

        if self.methods:
            stub += textwrap.indent("\n".join(map(str, self.methods)), "    ")
            stub += "\n"

        return stub.strip()


CodeChildNodeType = Union[
    ast.Assign, ast.AnnAssign, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef
]


class CodeStubBuilder(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.stub = None
        self.excludes = None

    def build(self, node: ast.ClassDef, excludes: Iterable[str]) -> "ClassStub":
        self.stub = CodeStub()
        self.excludes = set(excludes)
        self.visit(node)
        return self.stub

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Module):
            return super().visit(node)

        if isinstance(node, ImportNodeType.__args__):
            self.stub.blocks.append(ImportInfo.from_node(node))

        elif isinstance(node, ast.ClassDef) and self._check_name(node.name):
            is_class_exclude = lambda x: "." in x and x.split(".")[0] == node.name
            class_excludes = map(
                lambda x: x.split(".").pop(), filter(is_class_exclude, self.excludes)
            )
            self.stub.blocks.append(ClassStub.from_node(node, class_excludes))

        elif isinstance(node, FunctionNodeType.__args__) and self._check_name(
            node.name
        ):
            self.stub.blocks.append(FunctionStub.from_node(node))

        elif (
            isinstance(node, ast.Assign)
            and any(filter(self._check_name, map(ast.unparse, node.targets)))
        ) or (
            isinstance(node, ast.AnnAssign)
            and self._check_name(ast.unparse(node.target))
        ):
            self.stub.blocks.append(AssignInfo.from_node(node))

    def _check_name(self, name: str) -> bool:
        return not (name in self.excludes or name.startswith("_"))


CodeBlockType = Union[ImportInfo, ClassStub, FunctionStub, AssignInfo]

@dataclass
class CodeStub:
    blocks: List[CodeBlockType] = field(default_factory=list)

    @classmethod
    def from_module(
        cls, module: ModuleType, excludes: Iterable[str] = []
    ) -> "CodeStub":
        source = inspect.getsource(module)
        root = ast.parse(source)
        return CodeStubBuilder().build(root, excludes)

    def __repr__(self) -> str:
        stub = ""
        prev = None

        for block in self.blocks:
            if not prev:
                stub += f"{block}\n"
                prev = block
                continue

            if type(prev) != type(block) or isinstance(block, ClassStub):
                stub += "\n"

            stub += f"{block}\n"
            prev = block

        return stub
