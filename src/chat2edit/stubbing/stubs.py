import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type, Union

from pydantic import Field

from chat2edit.internal.exceptions import InvalidArgException
from chat2edit.utils.ast import get_ast_node, get_node_doc
from chat2edit.utils.repr import anno_repr


@dataclass
class ImportInfo:
    names: Tuple[str, Optional[str]]
    module: Optional[str] = field(default=None)
    
    @classmethod
    def from_node(cls, node: Union[ast.Import, ast.ImportFrom]) -> "ImportInfo":
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            raise InvalidArgException("node", Union[ast.Import, ast.ImportFrom], node)
        
        names = [(name.name, ast.unparse(name.asname) if name.asname else None) for name in node.names]
        
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


@dataclass
class AssignInfo:
    targets: List[str]
    value: Optional[str] = field(default=None)
    operator: Optional[str] = field(default=None)
    annotation: Optional[str] = field(default=None)

    @classmethod
    def from_node(
        cls, node: Union[ast.Assign, ast.AnnAssign, ast.AugAssign]
    ) -> "AssignInfo":
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

        if isinstance(node, ast.AugAssign):
            return cls(
                targets=[ast.unparse(node.target)],
                value=ast.unparse(node.value),
                operator=ast.unparse(node.op),
            )

        raise InvalidArgException(
            "node", Union[ast.Assign, ast.AnnAssign, ast.AugAssign], node
        )

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
        if self.annotation:
            return f"{self.targets[0]}: {self.annotation}{f' = {self.value}' if self.value else ''}"

        if self.operator:
            return f"f{self.targets[0]} {self.operator} {self.value}"

        return f"{' = '.join(self.targets)}{f' = {self.value}' if self.value else ''}"


@dataclass
class FunctionStub:
    name: str
    signature: str
    coroutine: bool = field(default=False)
    docstring: Optional[str] = field(default=None)
    decorators: List[str] = field(default_factory=list)

    @classmethod
    def from_node(
        cls, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> "FunctionStub":
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise InvalidArgException(
                "node", Union[ast.FunctionDef, ast.AsyncFunctionDef], node
            )

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

    def visit_Assign(self, node: ast.Assign) -> Any:
        if self._check_node(node):
            self.stub.attributes.append(AssignInfo.from_node(node))

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if self._check_node(node):
            self.stub.attributes.append(AssignInfo.from_node(node))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if self._check_node(node):
            self.stub.methods.append(FunctionStub.from_node(node))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        if self._check_node(node):
            self.stub.methods.append(FunctionStub.from_node(node))

    def _check_node(
        self,
        node: Union[ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef],
    ) -> bool:
        is_excluded = lambda x: x in self.excludes or x.startswith("_")

        if isinstance(node, ast.Assign):
            return not any(filter(is_excluded, map(ast.unparse, node.targets)))

        if isinstance(node, ast.AnnAssign):
            return not is_excluded(ast.unparse(node.target))

        return not is_excluded(node.name)


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
        stub += textwrap.indent("\n".join(map(str, self.attributes)), "    ")
        stub += "\n"
        stub += textwrap.indent("\n".join(map(str, self.methods)), "    ")

        return stub
    
    
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

    def visit_Import(self, node: ast.Import) -> Any:
        self.stub.blocks.append(ImportInfo.from_node(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        self.stub.blocks.append(ImportInfo.from_node(node))
            
    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if self._check_node(node):
            is_class_exclude = lambda x: "." in x and x.split(".")[0] == node.name
            class_excludes = map(lambda x: x.split(".").pop(), filter(is_class_exclude, self.excludes))
            self.stub.blocks.append(ClassStub.from_node(node, class_excludes))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if self._check_node(node):
            self.stub.methods.append(FunctionStub.from_node(node))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        if self._check_node(node):
            self.stub.methods.append(FunctionStub.from_node(node))
            
    def visit_Assign(self, node: ast.Assign) -> Any:
        if self._check_node(node):
            self.stub.blocks.append(AssignInfo.from_node(node))
            
    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        if self._check_node(node):
            self.stub.blocks.append(AssignInfo.from_node(node))

    def _check_node(
        self,
        node: Union[ast.Assign, ast.AnnAssign, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef],
    ) -> bool:
        is_excluded = lambda x: x in self.excludes or x.startswith("_")

        if isinstance(node, ast.Assign):
            return not any(filter(is_excluded, map(ast.unparse, node.targets)))

        if isinstance(node, ast.AnnAssign):
            return not is_excluded(ast.unparse(node.target))

        return not is_excluded(node.name)


@dataclass
class CodeStub:
    blocks: List[Union[ImportInfo, ClassStub, FunctionStub, AssignInfo]] = field(
        default_factory=list
    )
    
    @classmethod
    def from_module(cls, module: ModuleType, excludes: Iterable[str] = []) -> "CodeStub":
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
            
            if type(prev) != type(block) or isinstance(block, (ClassStub, FunctionStub)):
                stub += "\n"

            stub += f"{block}\n"
            prev = block
            
        return stub