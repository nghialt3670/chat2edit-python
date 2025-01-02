import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from chat2edit.prompting.stubbing.constants import (
    ATTRIBUTE_MAP_FUNCTION_KEY,
    ATTRIBUTE_TO_ALIAS_KEY,
    BASE_TO_ALIAS_KEY,
    COROUTINE_EXCLUDED_KEY,
    DOCSTRING_EXCLUDED_KEY,
    EXCLUDED_ATTRIBUTES_KEY,
    EXCLUDED_BASES_KEY,
    EXCLUDED_DECORATORS_KEY,
    EXCLUDED_METHODS_KEY,
    INCLUDED_ATTRIBUTES_KEY,
    INCLUDED_BASES_KEY,
    INCLUDED_DECORATORS_KEY,
    INCLUDED_METHODS_KEY,
    METHOD_MAP_FUNCTION_KEY,
    METHOD_TO_ALIAS_KEY,
    PARAMETER_TO_ALIAS_KEY,
)
from chat2edit.prompting.stubbing.replacers import (
    AttributeReplacer,
    MethodReplacer,
    ParameterReplacer,
)
from chat2edit.prompting.stubbing.utils import (
    find_shortest_import_path,
    get_ast_node,
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
    function: Optional[Callable] = field(default=None)

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
        stub = cls.from_node(node)
        stub.function = func
        return stub

    def generate(self) -> str:
        dec_names = set(dec.split("(")[0] for dec in self.decorators)
        docstring = (
            False
            if self.function and hasattr(self.function, DOCSTRING_EXCLUDED_KEY)
            else self.docstring
        )
        coroutine = (
            False
            if self.function and hasattr(self.function, COROUTINE_EXCLUDED_KEY)
            else self.coroutine
        )
        name = self.function.__name__ if self.function else self.name
        signature = self.signature

        param_to_alias = getattr(self, PARAMETER_TO_ALIAS_KEY, None)

        if included_decs := getattr(self.function, INCLUDED_DECORATORS_KEY, None):
            dec_names.intersection_update(included_decs)

        if excluded_decs := getattr(self.function, EXCLUDED_DECORATORS_KEY, None):
            dec_names.difference_update(excluded_decs)

        decorators = filter(lambda x: x.split("(")[0] in dec_names, self.decorators)

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

        if param_to_alias:
            stub = ParameterReplacer.replace(stub, param_to_alias)

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
    clss: Optional[Type] = field(default=None)

    @classmethod
    def from_node(cls, node: ast.ClassDef) -> "ClassStub":
        from chat2edit.prompting.stubbing.builders import ClassStubBuilder

        return ClassStubBuilder().build(node)

    @classmethod
    def from_class(cls, clss: Type[Any]) -> "ClassStub":
        node = get_ast_node(clss)
        stub = cls.from_node(node)

        for i, method_stub in enumerate(stub.methods):
            method = getattr(clss, method_stub.name)

            if callable(method):
                stub.methods[i] = FunctionStub.from_function(method)

        stub.clss = clss
        return stub

    def generate(
        self,
        included_attrs: List[str] = [],
        excluded_attrs: List[str] = [],
        included_methods: List[str] = [],
        excluded_methods: List[str] = [],
        indent_spaces: int = 4,
    ) -> str:
        dec_names = set(dec.split("(")[0] for dec in self.decorators)
        name = self.clss.__name__ if self.clss else self.name
        bases = set(self.bases)
        docstring = (
            None
            if self.clss and hasattr(self.clss, DOCSTRING_EXCLUDED_KEY)
            else self.docstring
        )
        attr_names = set(attr.target for attr in self.attributes)
        method_names = set(method.name for method in self.methods)

        attr_to_alias = getattr(self.clss, ATTRIBUTE_TO_ALIAS_KEY, None)
        attr_map_func = getattr(self.clss, ATTRIBUTE_MAP_FUNCTION_KEY, None)

        method_to_alias = getattr(self.clss, METHOD_TO_ALIAS_KEY, None)
        method_map_func = getattr(self.clss, METHOD_MAP_FUNCTION_KEY, None)

        base_to_alias = getattr(self.clss, BASE_TO_ALIAS_KEY, None)

        if included_attrs:
            attr_names.intersection_update(included_attrs)

        if excluded_attrs:
            attr_names.difference_update(excluded_attrs)

        if included_methods:
            method_names.intersection_update(included_methods)

        if excluded_methods:
            method_names.difference_update(excluded_methods)

        if included_decs := getattr(self.clss, INCLUDED_DECORATORS_KEY, None):
            dec_names.intersection_update(included_decs)

        if excluded_decs := getattr(self.clss, EXCLUDED_DECORATORS_KEY, None):
            dec_names.difference_update(excluded_decs)

        if included_bases := getattr(self.clss, INCLUDED_BASES_KEY, None):
            bases.intersection_update(included_bases)

        if excluded_bases := getattr(self.clss, EXCLUDED_BASES_KEY, None):
            bases.difference_update(excluded_bases)

        if included_attrs := getattr(self.clss, INCLUDED_ATTRIBUTES_KEY, None):
            attr_names.intersection_update(included_attrs)

        if excluded_attrs := getattr(self.clss, EXCLUDED_ATTRIBUTES_KEY, None):
            attr_names.difference_update(excluded_attrs)

        if included_methods := getattr(self.clss, INCLUDED_METHODS_KEY, None):
            method_names.intersection_update(included_methods)

        if excluded_methods := getattr(self.clss, EXCLUDED_METHODS_KEY, None):
            method_names.difference_update(excluded_methods)

        decorators = filter(lambda x: x.split("(")[0] in dec_names, self.decorators)

        if base_to_alias:
            bases = list(bases)
            for i, base in enumerate(bases):
                bases[i] = base_to_alias.get(base, base)

        attributes = [
            attr
            for attr in self.attributes
            if attr.target in attr_names and not attr.target.startswith("_")
        ]

        if attr_map_func:
            for attr in attributes:
                attr.target = attr_map_func(attr.target)

        methods = [
            method
            for method in self.methods
            if method.name in method_names and not method.name.startswith("_")
        ]

        for method in methods:
            # Prevent method from being decorated by @alias
            if method.function:
                method.function.__name__ = method.name

            if method_map_func:
                method.name = method_map_func(method.name)

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

        if attr_to_alias:
            stub = AttributeReplacer.replace(stub, attr_to_alias)

        if method_to_alias:
            stub = MethodReplacer.replace(stub, method_to_alias)

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

                if stub.name != k:
                    mappings[stub.name] = k
                elif stub.clss and stub.name != stub.clss.__name__:
                    mappings[stub.name] = stub.clss.__name__

                blocks.append(stub)

            elif inspect.isfunction(v):
                stub = FunctionStub.from_function(v)

                if stub.name != k:
                    mappings[stub.name] = k
                elif stub.function and stub.name != stub.function.__name__:
                    mappings[stub.name] = stub.function.__name__

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
            for k, v in self.mappings.items():
                stub = stub.replace(k, v)

        return stub.strip()

    def __repr__(self) -> str:
        return self.generate()
