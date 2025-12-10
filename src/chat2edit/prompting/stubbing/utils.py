import ast
import inspect
import re
import sys
import textwrap
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def get_ast_node(target: Any) -> ast.AST:
    root = ast.walk(ast.parse(textwrap.dedent(inspect.getsource(target))))
    next(root)
    return next(root)


def get_node_doc(node: ast.AST) -> Optional[str]:
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        return node.body[0].value.value

    return None


def get_call_args(call: str) -> str:
    return re.search(r"\((.*?)\)", call).group(1)


def is_external_package(obj: Any) -> bool:
    """
    Determine if an object comes from an external package.

    A package is considered external if it's:
    1. From site-packages (installed packages)
    2. From the standard library
    3. A built-in module

    Otherwise, it's considered part of the user's project (internal).
    """
    if inspect.isclass(obj) or inspect.isfunction(obj):
        module_name = obj.__module__
    else:
        try:
            module_name = obj.__class__.__module__
        except AttributeError:
            module_name = type(obj).__module__

    # Built-in modules are external
    if module_name in sys.builtin_module_names:
        return True

    # Get the module object
    module = sys.modules.get(module_name)
    if module is None:
        return True

    # If module has no __file__, it's likely built-in or special
    if not hasattr(module, "__file__") or module.__file__ is None:
        return True

    module_path = Path(module.__file__).resolve()

    # Check if it's in site-packages or dist-packages
    for path in sys.path:
        site_pkg_path = Path(path).resolve()
        if "site-packages" in str(site_pkg_path) or "dist-packages" in str(site_pkg_path):
            try:
                if site_pkg_path in module_path.parents or site_pkg_path == module_path.parent:
                    return True
            except (ValueError, OSError):
                continue

    # Check if it's from the standard library
    # Standard library is usually in the Python installation directory
    stdlib_paths = [Path(p).resolve() for p in sys.path if "lib" in p and "site-packages" not in p]
    for stdlib_path in stdlib_paths:
        try:
            if stdlib_path in module_path.parents:
                return True
        except (ValueError, OSError):
            continue

    # If none of the above, it's part of the user's project (internal)
    return False


def find_shortest_import_path(obj: Any) -> str:
    candidates = []

    for name, module in list(sys.modules.items()):
        if module and getattr(module, obj.__name__, None) is obj:
            candidates.append(name)

    candidates = [c for c in candidates if not c.startswith("__")]

    # If no candidates found after filtering, fall back to the object's module
    if not candidates:
        obj_module = inspect.getmodule(obj)
        if obj_module is not None:
            module_name = obj_module.__name__
            # Only return if it doesn't start with "__"
            if not module_name.startswith("__"):
                return module_name
        # Last resort: try to get module from object's __module__ attribute
        if hasattr(obj, "__module__") and obj.__module__:
            module_name = obj.__module__
            if not module_name.startswith("__"):
                return module_name
        # If all else fails, raise a more informative error
        raise ValueError(
            f"Could not find import path for {obj.__name__} (type: {type(obj).__name__}). "
            f"Object module: {getattr(obj, '__module__', 'unknown')}"
        )

    return min(candidates, key=len)


def extend_list_attr(target: Any, attr: str, values: Iterable[Any]) -> None:
    setattr(target, attr, list(chain(getattr(target, attr, []), values)))


def append_list_attr(target: Any, attr: str, value: Any) -> None:
    extend_list_attr(target, attr, [value])


def update_dict_attr(target: Any, attr: str, update: Dict) -> None:
    d = getattr(target, attr, {})
    d.update(update)
    setattr(target, attr, d)
