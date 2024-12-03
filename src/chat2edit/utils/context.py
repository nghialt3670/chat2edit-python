import inspect
import sys
from collections import deque
from typing import Any


def obj_to_path(obj: Any, root: Any) -> str:
    visited = set()
    queue = deque([(root, "root")])

    while queue:
        current, path = queue.popleft()
        obj_id = id(current)

        if obj_id in visited:
            continue

        visited.add(obj_id)

        if current is obj:
            return path if path != "root" else "root"

        if isinstance(current, dict):
            for key, value in current.items():
                new_path = f"{path}.{key}" if path != "root" else key
                queue.append((value, new_path))

        elif isinstance(current, (list, tuple)):
            for index, item in enumerate(current):
                new_path = f"{path}[{index}]"
                queue.append((item, new_path))

        elif hasattr(current, "__dict__"):
            for attr, value in current.__dict__.items():
                new_path = f"{path}.{attr}" if path != "root" else attr
                queue.append((value, new_path))

    return None


def path_to_obj(path: str, root: Any) -> Any:
    current = root
    parts = path.split(".")

    for part in parts:
        if "[" in part and "]" in part:
            key, indices = part.split("[", 1)
            indices = indices.rstrip("]")
            if key:
                current = current[key]
            current = current[int(indices)]
        else:
            if isinstance(current, dict):
                current = current[part]
            elif hasattr(current, "__dict__"):
                current = getattr(current, part)
            else:
                raise ValueError(f"Invalid path: {part} in {path}")

    return current


def is_external_package(obj: Any) -> bool:
    if inspect.isclass(obj) or inspect.isfunction(obj):
        module_name = obj.__module__
    else:
        try:
            module_name = obj.__class__.__module__
        except AttributeError:
            module_name = type(obj).__module__

    return not module_name.startswith(__name__.split(".")[0])


def find_shortest_import_path(obj: Any) -> str:
    candidates = []

    for name, module in list(sys.modules.items()):
        if module and getattr(module, obj.__name__, None) is obj:
            candidates.append(name)

    candidates = [c for c in candidates if not c.startswith("__")]
    return min(candidates, key=len)
