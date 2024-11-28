from typing import Any, Dict, List, Tuple, get_args, get_origin


def validate_type(value: Any, anno: Any) -> bool:
    """
    Validate a value against a type annotation with support for generic types.

    Args:
        value: The value to validate
        anno: The type annotation to validate against

    Returns:
        bool: True if the value matches the type annotation, False otherwise
    """
    # Handle Optional types
    if hasattr(anno, "__origin__") and anno.__origin__ is None:
        return value is None

    # Get the base origin type (e.g., List, Dict, etc.)
    origin_type = get_origin(anno)

    # If no origin type, do a simple isinstance check
    if origin_type is None:
        return isinstance(value, anno)

    # Check if the value matches the origin type (e.g., list, dict)
    if not isinstance(value, origin_type):
        return False

    # Get the type arguments (e.g., for List[int], get [int])
    type_args = get_args(anno)

    # If no type arguments, we've already confirmed the base type
    if not type_args:
        return True

    # For generic types with type arguments, validate each element
    if origin_type in (list, List):
        return all(validate_type(item, type_args[0]) for item in value)

    elif origin_type in (dict, Dict):
        key_type, value_type = type_args
        return all(validate_type(k, key_type) for k in value.keys()) and all(
            validate_type(v, value_type) for v in value.values()
        )

    elif origin_type in (tuple, Tuple):
        # Handle fixed-length tuples
        if len(type_args) == len(value):
            return all(validate_type(v, t) for v, t in zip(value, type_args))

        # Handle variable-length tuples (with ellipsis)
        elif type_args and type_args[-1] is ...:
            base_type = type_args[0]
            return all(validate_type(v, base_type) for v in value)

    # Fallback to isinstance for other types
    return isinstance(value, origin_type)
