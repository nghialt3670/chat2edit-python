from collections import deque
from typing import Any


def value_to_path(value: Any, root: Any) -> str:
    visited = set()
    queue = deque([(root, "root")])

    while queue:
        current, path = queue.popleft()
        value_id = id(current)

        if value_id in visited:
            continue

        visited.add(value_id)

        if current is value:
            return path if path != "root" else "root"

        if isinstance(current, dict):
            for key, val in current.items():
                new_path = f"{path}.{key}" if path != "root" else key
                queue.append((val, new_path))

        elif isinstance(current, (list, tuple)):
            for index, item in enumerate(current):
                new_path = f"{path}[{index}]"
                queue.append((item, new_path))

        elif hasattr(current, "__dict__"):
            for attr, val in current.__dict__.items():
                new_path = f"{path}.{attr}" if path != "root" else attr
                queue.append((val, new_path))

    return None
