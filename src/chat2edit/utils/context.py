from collections import deque
from typing import Any


def obj_to_path(root, obj) -> str:
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


def path_to_obj(root: Any, path: str) -> Any:
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
