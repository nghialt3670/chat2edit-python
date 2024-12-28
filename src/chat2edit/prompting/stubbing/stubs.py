import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from chat2edit.prompting.stubbing.decorators import STUBBING_DECORATORS
from chat2edit.prompting.stubbing.replacers import (
    AttributeReplacer,
    NameReplacer,
    ParameterReplacer,
)
from chat2edit.prompting.stubbing.utils import (
    find_shortest_import_path,
    get_ast_node,
    get_call_args,
    get_node_doc,
    is_external_package,
)

ImportNodeType = Union[ast.Import, ast.ImportFrom]


@dataclass
class ImportInfo:
    names: Tuple[str, Optional[str]]
    module: Optional[str] = field(default=None)

    @classmethod
    def from_node(cls, node: ImportNodeType) -> "ImportInfo":
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
        r = f"from {self.module} import " if self.module else "import "
        r += ", ".join(map(lambda x: f"{x[0]} as {x[1]}" if x[1] else x[0], self.names))
        return r


AssignNodeType = Union[ast.Assign, ast.AnnAssign]


@dataclass
class AssignInfo:
    target: str
    value: Optional[str] = field(default=None)
    annotation: Optional[str] = field(default=None)

    @classmethod
    def from_node(cls, node: AssignNodeType) -> "AssignInfo":
        if isinstance(node, ast.Assign):
            return cls(
                target=list(map(ast.unparse, node.targets))[0],
                value=ast.unparse(node.value),
            )

        return cls(
            target=[ast.unparse(node.target)][0],
            value=ast.unparse(node.value) if node.value else None,
            annotation=ast.unparse(node.annotation),
        )

    def __repr__(self) -> str:
        r = self.target

        if self.annotation:
            r += f": {self.annotation}"

        if self.value:
            r += f" = {self.value}"

        return r


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
    def from_function(cls, func: Callable) -> "FunctionStub":
        node = get_ast_node(func)
        return cls.from_node(node)

    def generate(self) -> str:
        name = self.name
        signature = self.signature
        coroutine = self.coroutine
        docstring = self.docstring
        decorators = self.decorators
        param_mappings = {}

        for dec in self.decorators:
            if dec.startswith("alias"):
                name = eval(get_call_args(dec))

            elif dec == "exclude_docstring":
                docstring = None

            elif dec == "exclude_coroutine":
                coroutine = False

            if dec.startswith("include_decorators"):
                included_decorators = eval(get_call_args(dec))
                decorators.intersection_update(included_decorators)

            if dec.startswith("exclude_decorators"):
                excluded_decorators = eval(get_call_args(dec))
                decorators.difference_update(excluded_decorators)

            if dec.startswith("parameter_aliases"):
                param_mappings = eval(get_call_args(dec))

        decorators = [dec for dec in decorators if dec not in STUBBING_DECORATORS]

        stub = ""

        if decorators:
            for dec in decorators:
                stub += f"@{dec}\n"

        if docstring:
            for line in docstring.split("\n"):
                stub += f"# {line}\n"

        if coroutine:
            stub += "async "

        stub += f"def {name}{signature}: ..."

        if param_mappings:
            stub = ParameterReplacer.replace(stub, param_mappings)

        return stub

    def __repr__(self) -> str:
        return self.generate()


@dataclass
class ClassStub:
    name: str
    bases: List[str] = field(default_factory=list)
    attributes: List[AssignInfo] = field(default_factory=list)
    methods: List[FunctionStub] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = field(default=None)

    @classmethod
    def from_node(cls, node: ast.ClassDef) -> "ClassStub":
        from chat2edit.prompting.stubbing.builders import ClassStubBuilder

        return ClassStubBuilder().build(node)

    @classmethod
    def from_class(cls, clss: Type[Any]) -> "ClassStub":
        node = get_ast_node(clss)
        stub = cls.from_node(node)
        return stub

    def generate(
        self,
        included_attributes: List[str] = [],
        excluded_attributes: List[str] = [],
        included_methods: List[str] = [],
        excluded_methods: List[str] = [],
        indent_spaces: int = 4,
    ) -> str:
        name = self.name
        docstring = self.docstring
        decorators = set(self.decorators)
        bases = set(self.bases)
        attributes = set(attr.target for attr in self.attributes)
        methods = set(method.name for method in self.methods)
        attr_mappings = {}
        base_mappings = {}

        if included_attributes:
            attributes.intersection_update(included_attributes)

        attributes.difference_update(excluded_attributes)

        if included_methods:
            methods.intersection_update(included_methods)

        methods.difference_update(excluded_methods)

        for dec in self.decorators:
            if dec.startswith("alias"):
                name = eval(get_call_args(dec))

            if dec.startswith("base_aliases"):
                base_mappings = eval(get_call_args(dec))

            if dec == "exclude_docstring":
                docstring = None

            if dec.startswith("include_decorators"):
                included_decorators = eval(get_call_args(dec))
                decorators.intersection_update(included_decorators)

            if dec.startswith("exclude_decorators"):
                excluded_decorators = eval(get_call_args(dec))
                decorators.difference_update(excluded_decorators)

            if dec.startswith("include_bases"):
                included_bases = eval(get_call_args(dec))
                bases.intersection_update(included_bases)

            if dec.startswith("exclude_bases"):
                excluded_bases = eval(get_call_args(dec))
                bases.difference_update(excluded_bases)

            if dec.startswith("include_attributes"):
                included_attributes = eval(get_call_args(dec))
                attributes.intersection_update(included_attributes)

            if dec.startswith("exclude_attributes"):
                excluded_attributes = eval(get_call_args(dec))
                attributes.difference_update(excluded_attributes)

            if dec.startswith("include_methods"):
                included_methods = eval(get_call_args(dec))
                methods.intersection_update(included_methods)

            if dec.startswith("exclude_methods"):
                excluded_methods = eval(get_call_args(dec))
                methods.difference_update(excluded_methods)

            if dec.startswith("attribute_aliases"):
                attr_mappings = eval(get_call_args(dec))

        bases = list(bases)
        for i, base in enumerate(bases):
            bases[i] = base_mappings.get(base, base)

        attributes = [
            attr
            for attr in self.attributes
            if attr.target in attributes and not attr.target.startswith("_")
        ]
        methods = [
            method
            for method in self.methods
            if method.name in methods and not method.name.startswith("_")
        ]
        decorators = filter(
            lambda x: x.split("(")[0] not in STUBBING_DECORATORS, decorators
        )

        stub = ""
        indent = " " * indent_spaces

        if decorators:
            for dec in decorators:
                stub += f"@{dec}\n"

        stub += f"class {name}"

        if bases:
            stub += f"({', '.join(bases)})"

        stub += ":\n"

        if docstring:
            stub += textwrap.indent('"""\n', indent)
            stub += textwrap.indent(f"{docstring}\n", indent)
            stub += textwrap.indent('"""\n', indent)

        if not attributes and not methods:
            stub += f"{indent}pass"
            return stub

        if attributes:
            stub += textwrap.indent("\n".join(map(str, attributes)), indent)
            stub += "\n"

        if methods:
            stub += textwrap.indent("\n".join(map(str, methods)), indent)
            stub += "\n"

        if attr_mappings:
            stub = AttributeReplacer.replace(stub, attr_mappings)

        return stub.strip()

    def __repr__(self) -> str:
        return self.generate()


CodeBlockType = Union[ImportInfo, ClassStub, FunctionStub]


@dataclass
class CodeStub:
    mappings: Dict[str, str] = field(default_factory=dict)
    blocks: List[CodeBlockType] = field(default_factory=list)

    @classmethod
    def from_module(cls, module: ModuleType) -> "CodeStub":
        source = inspect.getsource(module)
        root = ast.parse(source)
        from chat2edit.prompting.stubbing.builders import CodeStubBuilder

        return CodeStubBuilder().build(root)

    @classmethod
    def from_context(cls, context: Dict[str, Any]) -> "CodeStub":
        mappings = {}
        blocks = []

        for k, v in context.items():
            if not inspect.isclass(v) and not inspect.isfunction(v):
                continue

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
                stub = FunctionStub.from_function(v)
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
            stub = NameReplacer.replace(stub, self.mappings)

        return stub.strip()

    def __repr__(self) -> str:
        return self.generate()
