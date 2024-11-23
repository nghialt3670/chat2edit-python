import inspect
import re
from dataclasses import asdict
from textwrap import indent
from typing import Any, Dict, List, Type

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


def anno_repr(anno: Any) -> str:
    """Generate a cleaner representation for an annotation."""

    if hasattr(anno, "__origin__"):
        origin_repr = anno.__origin__.__name__.capitalize()

        if hasattr(anno, "__args__"):
            args_repr = ", ".join(map(anno_repr, anno.__args__))
            return f"{origin_repr}[{args_repr}]"

        return origin_repr

    elif isinstance(anno, type):
        return str(anno.__name__)

    else:
        return str(anno)


def to_snake_case(text: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def get_class_stub(
    cls: Type[Any], excludes: List[str] = [], exclude_private: bool = True
) -> str:
    base_classes = [base.__name__ for base in cls.__bases__ if base is not object]
    base_classes_repr = f"({', '.join(base_classes)})" if base_classes else ""

    attr_name_to_signature = get_cls_attr_name_to_signature(cls)
    method_name_to_stub = get_cls_method_name_to_stub(cls)

    check_member_name = lambda x: not (
        (exclude_private and x.startswith("_")) or x in excludes
    )

    attr_signatures = [
        signature
        for name, signature in attr_name_to_signature.items()
        if check_member_name(name)
    ]
    method_stubs = [
        stub for name, stub in method_name_to_stub.items() if check_member_name(name)
    ]

    stub = f"class {cls.__name__}{base_classes_repr}:\n"

    if not attr_signatures and not method_stubs:
        stub += "    pass\n"
    else:
        stub += indent("\n".join(attr_signatures + method_stubs), "    ")

    return stub


def get_function_stub(func: Any) -> str:
    params_anno_dict = {k: v for k, v in func.__annotations__.items() if k != "return"}
    params_anno_repr = ", ".join(
        f"{k}: {anno_repr(v)}" for k, v in params_anno_dict.items()
    )

    return_anno = func.__annotations__.get("return", None)
    return_anno_repr = f" -> {anno_repr(return_anno)}" if return_anno else ""

    return f"def {func.__name__}({params_anno_repr}){return_anno_repr}: ..."


def get_cls_attr_name_to_signature(cls: Type[Any]) -> Dict[str, str]:
    annotations = getattr(cls, "__annotations__", {})
    fields = getattr(cls, "__fields__", {})

    name_to_signature = {}

    for attr_name, attr_type in annotations.items():
        attr_type_repr = anno_repr(attr_type)
        attr_signature = None

        field = fields.get(attr_name)

        # Pydantic Field
        if isinstance(field, FieldInfo):
            field_args_dict = {}

            if field.default is not PydanticUndefined:
                field_args_dict["default"] = repr(field.default)

            if field.default_factory is not None:
                field_args_dict["default_factory"] = field.default_factory.__name__

            for metadata in field.metadata:
                for k, v in asdict(metadata).items():
                    field_args_dict[k] = v

            field_args_repr = ", ".join(f"{k}={v}" for k, v in field_args_dict.items())
            field_repr = f"Field({field_args_repr})"

            attr_signature = f"{attr_name}: {attr_type_repr} = {field_repr}"
        else:
            attr_signature = f"{attr_name}: {attr_type_repr}"

        name_to_signature[attr_name] = attr_signature

    return name_to_signature


def get_cls_method_name_to_stub(cls: Type[Any]) -> Dict[str, str]:
    return {
        name: get_function_stub(method)
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction)
    }
