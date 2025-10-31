from typing import Any


def path_to_value(path: str, root: Any) -> Any:
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
