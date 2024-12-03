import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from itertools import chain
from types import ModuleType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    get_args,
)

from chat2edit.constants import (
    CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY,
    CLASS_STUB_EXCLUDED_BASES_KEY,
    CLASS_STUB_EXCLUDED_METHODS_KEY,
    STUB_EXCLUDED_DECORATORS_KEY,
)
from chat2edit.internal.exceptions import (
    InvalidArgumentException,
    InvalidContextVariableException,
)
from chat2edit.utils.ast import get_ast_node, get_node_doc
from chat2edit.utils.code import replace_names
from chat2edit.utils.context import find_shortest_import_path, is_external_package
from chat2edit.utils.repr import anno_repr

ImportNodeType = Union[ast.Import, ast.ImportFrom]


@dataclass
class ImportInfo:
    names: Tuple[str, Optional[str]]
    module: Optional[str] = field(default=None)

    @classmethod
    def from_node(cls, node: ImportNodeType) -> "ImportInfo":
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            raise InvalidArgumentException("node", ImportNodeType, node)

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
        names = [(obj.__name__, None)]

        if obj_module == obj:
            return cls(names)

        module = find_shortest_import_path(obj)
        return cls(names, module)

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

        raise InvalidArgumentException("node", AssignNodeType, node)

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
    func: Optional[Callable] = field(default=None)
    coroutine: bool = field(default=False)
    docstring: Optional[str] = field(default=None)
    decorators: List[str] = field(default_factory=list)

    @classmethod
    def from_node(cls, node: FunctionNodeType) -> "FunctionStub":
        if not isinstance(node, get_args(FunctionNodeType)):
            raise InvalidArgumentException("node", FunctionNodeType, node)

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
        stub = cls.from_node(node)
        stub.func = func
        return stub

    def generate(self, excluded_decorators: Iterable[str] = []) -> str:
        stub = ""

        excluded_decorators = set(
            chain(
                excluded_decorators,
                getattr(self.func, STUB_EXCLUDED_DECORATORS_KEY, []),
            )
        )
        is_included_decorator = lambda x: x not in excluded_decorators
        included_decorators = list(filter(is_included_decorator, self.decorators))

        if included_decorators:
            stub += "\n".join(map(lambda x: f"@{x}", included_decorators))
            stub += "\n"

        if self.coroutine:
            stub += "async "

        stub += f"def {self.name}{self.signature}: ..."

        return stub

    def __repr__(self) -> str:
        return self.generate()


@dataclass
class ClassStub:
    name: str
    clss: Optional[Type[Any]] = field(default=None)
    bases: List[str] = field(default_factory=list)
    attributes: List[AssignInfo] = field(default_factory=list)
    methods: List[FunctionStub] = field(default_factory=list)
    docstring: Optional[str] = field(default=None)
    decorators: List[str] = field(default_factory=list)

    @classmethod
    def from_node(cls, node: ast.ClassDef) -> "ClassStub":
        if not isinstance(node, ast.ClassDef):
            raise InvalidArgumentException("node", ast.ClassDef, node)

        from chat2edit.stubbing.builders import ClassStubBuilder

        return ClassStubBuilder().build(node)

    @classmethod
    def from_class(cls, clss: Type[Any]) -> "ClassStub":
        node = get_ast_node(clss)
        stub = cls.from_node(node)
        stub.clss = clss
        return stub

    def generate(
        self,
        *,
        excluded_decorators: Iterable[str] = [],
        excluded_bases: Iterable[str] = [],
        excluded_attributes: Iterable[str] = [],
        excluded_methods: Iterable[str] = [],
        exclude_private_decorators: bool = True,
        exclude_private_bases: bool = True,
        exclude_private_attributes: bool = True,
        exclude_private_methods: bool = True,
        indent_spaces: int = 4,
    ) -> str:
        excluded_bases = set(
            chain(excluded_bases, getattr(self.clss, CLASS_STUB_EXCLUDED_BASES_KEY, []))
        )
        excluded_decorators = set(
            chain(
                excluded_decorators,
                getattr(self.clss, STUB_EXCLUDED_DECORATORS_KEY, []),
            )
        )
        excluded_attributes = set(
            chain(
                excluded_attributes,
                getattr(self.clss, CLASS_STUB_EXCLUDED_ATTRIBUTES_KEY, []),
            )
        )
        excluded_methods = set(
            chain(
                excluded_methods,
                getattr(self.clss, CLASS_STUB_EXCLUDED_METHODS_KEY, []),
            )
        )

        is_private = lambda x: x.startswith("_")
        get_decorator_name = lambda x: x.split("(")[0]

        is_included_decorator = lambda x: get_decorator_name(
            x
        ) not in excluded_decorators and not (
            exclude_private_decorators and is_private(get_decorator_name(x))
        )
        is_included_base = lambda x: x not in excluded_bases and not (
            exclude_private_bases and is_private(x)
        )
        is_included_attribute = lambda x: all(
            map(lambda i: i not in excluded_attributes, x.targets)
        ) and not (exclude_private_attributes and any(map(is_private, x.targets)))
        is_included_method = lambda x: x.name not in excluded_methods and not (
            exclude_private_methods and is_private(x.name)
        )

        included_decorators = filter(is_included_decorator, self.decorators)
        included_bases = list(filter(is_included_base, self.bases))
        included_atttributes = list(filter(is_included_attribute, self.attributes))
        included_methods = list(filter(is_included_method, self.methods))

        stub = ""
        indent = " " * indent_spaces

        for dec in included_decorators:
            stub += f"@{dec}\n"

        stub += f"class {self.name}"

        if included_bases:
            stub += f"({', '.join(included_bases)})"

        stub += ":\n"

        if not included_atttributes and not included_methods:
            stub += f"{indent}pass"
            return stub

        if included_atttributes:
            stub += textwrap.indent("\n".join(map(str, included_atttributes)), indent)
            stub += "\n"

        if included_methods:
            stub += textwrap.indent(
                "\n".join(method.generate() for method in included_methods), indent
            )
            stub += "\n"

        return stub.strip()

    def __repr__(self) -> str:
        return self.generate()


CodeBlockType = Union[ImportInfo, ClassStub, FunctionStub, AssignInfo]


@dataclass
class CodeStub:
    mappings: Dict[str, str] = field(default_factory=dict)
    blocks: List[CodeBlockType] = field(default_factory=list)

    @classmethod
    def from_module(cls, module: ModuleType) -> "CodeStub":
        source = inspect.getsource(module)
        root = ast.parse(source)
        from chat2edit.stubbing.builders import CodeStubBuilder

        return CodeStubBuilder().build(root)

    @classmethod
    def from_context(cls, context: Dict[str, Any]) -> "CodeStub":
        mappings = {}
        blocks = []

        for k, v in context.items():
            if not inspect.isclass(v) and not inspect.isfunction(v):
                raise InvalidContextVariableException(k)

            if is_external_package(v):
                info = ImportInfo.from_obj(v)

                if k != v.__name__:
                    info.names[0] = (info.names[0][0], k)
                    mappings[v.__name__] = k

                blocks.append(info)

            elif inspect.isclass(v):
                stub = ClassStub.from_class(v)
                mappings[stub.name] = k
                blocks.append(stub)

            elif inspect.isfunction(v):
                stub = FunctionStub.from_func(v)
                mappings[stub.name] = k
                blocks.append(stub)

        return cls(mappings, blocks)

    def generate(self) -> str:
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

        if self.mappings:
            return replace_names(stub, self.mappings)

        return stub

    def __repr__(self) -> str:
        stub = ""
        prev = None

        for block in self.blocks:
            if not prev:
                if isinstance(block, (ClassStub, FunctionStub)):
                    stub += f"{block.generate()}\n"
                else:
                    stub += f"{block}\n"

                prev = block
                continue

            if type(prev) != type(block) or isinstance(block, ClassStub):
                stub += "\n"

            stub += f"{block}\n"
            prev = block

        return stub
