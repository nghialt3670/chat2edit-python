import ast
import inspect
import types
from typing import Any, Dict, Set

import astor
import black


class AsyncCallCorrector(ast.NodeTransformer):
    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        # Set to store all discovered async function/method names
        self.async_functions = set()
        self._collect_async_functions(context)

    def _collect_async_functions(
        self, obj: Any, prefix: str = "", visited: Set[int] = None
    ):
        """
        Recursively collect all async functions/methods from an object and its attributes
        """
        if visited is None:
            visited = set()

        # Avoid circular references
        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)

        # Skip certain types that shouldn't be traversed
        if isinstance(obj, (str, int, float, bool, bytes, types.ModuleType)):
            return

        # Check if the object itself is an async function
        if inspect.iscoroutinefunction(obj):
            if prefix:  # If it's a nested attribute
                self.async_functions.add(prefix.split(".")[-1])
            else:  # If it's a direct context value
                self.async_functions.add(obj.__name__)
            return

        try:
            # Handle dictionaries
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    self._collect_async_functions(value, new_prefix, visited)
                return

            # Get all attributes that we can examine
            if hasattr(obj, "__dict__"):
                items = [
                    (name, getattr(obj, name))
                    for name in dir(obj)
                    if not name.startswith("__")
                ]
            else:
                items = []

            # For classes, also check their methods
            if inspect.isclass(obj):
                class_items = inspect.getmembers(obj)
                items.extend(
                    class_item
                    for class_item in class_items
                    if not class_item[0].startswith("__")
                )

            # Process each attribute
            for name, value in items:
                # Skip properties to avoid potential side effects
                if isinstance(value, property):
                    continue

                new_prefix = f"{prefix}.{name}" if prefix else name

                # Check if it's an async function/method
                if inspect.iscoroutinefunction(value):
                    self.async_functions.add(name)

                # Recursively process the attribute
                try:
                    self._collect_async_functions(value, new_prefix, visited)
                except Exception:
                    # Skip any attributes that can't be accessed
                    continue

        except Exception:
            # Skip any objects that can't be inspected
            pass

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            # Handle direct function calls
            func_name = node.func.id
            if func_name in self.async_functions and not isinstance(
                getattr(node, "parent", None), ast.Await
            ):
                return ast.Await(value=node)

        elif isinstance(node.func, ast.Attribute):
            # Handle method calls (obj.method())
            method_name = node.func.attr
            if method_name in self.async_functions and not isinstance(
                getattr(node, "parent", None), ast.Await
            ):
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
