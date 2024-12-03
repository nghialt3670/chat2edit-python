from typing import Any, Type

from chat2edit.utils.repr import anno_repr


class InvalidArgumentException(Exception):
    def __init__(self, param: str, expect: Type[Any], received: Any) -> None:
        expect_type = anno_repr(expect)
        received_type = type(received).__name__
        super().__init__(
            f"Invalid argument for `{param}`: Expected type `{expect_type}`, but received type `{received_type}`."
        )


class InvalidContextVariableException(Exception):
    def __init__(self, varname: str) -> None:
        super().__init__(f"Invalid context variable: `{varname}`.")
