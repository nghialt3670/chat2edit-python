import inspect
from copy import deepcopy
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar

T = TypeVar("T")


class Attachment(Generic[T]):
    def __init__(
        self,
        obj: T,
        *,
        filename: Optional[str] = None,
        basename: Optional[str] = None,
        original: bool = True,
        attrpaths: List[str] = [],
        attachments: List[Any] = [],
    ) -> None:
        super().__init__()

        while isinstance(obj, Attachment):
            obj = obj.__obj__

        self.__dict__["__obj__"] = obj
        self.__dict__["__filename__"] = filename
        self.__dict__["__basename__"] = basename
        self.__dict__["__original__"] = original
        self.__dict__["__attrpaths__"] = attrpaths
        self.__dict__["__attachments__"] = attachments

    @property
    def __obj__(self) -> T:
        return self.__dict__["__obj__"]

    @property
    def __filename__(self) -> Optional[str]:
        return self.__dict__["__filename__"]

    @property
    def __basename__(self) -> Optional[str]:
        return self.__dict__["__basename__"]

    @property
    def __original__(self) -> bool:
        return self.__dict__["__original__"]

    @property
    def __attrpaths__(self) -> List[str]:
        return self.__dict__["__attrpaths__"]

    @property
    def __attachments__(self) -> List["Attachment"]:
        return self.__dict__["__attachments__"]

    @property
    def __class__(self) -> Type[T]:
        return self.__obj__.__class__

    def set_origin_modification_handler(
        self, handler: Callable[[str, str], None]
    ) -> None:
        self.__dict__["__origin_modification_handler__"] = handler

    def _handle_origin_modification(self, member: str) -> None:
        if handler := getattr(self, "__origin_modification_handler__", None):
            caller_frame = inspect.currentframe().f_back.f_back
            for k, v in caller_frame.f_locals.items():
                if v is self:
                    handler(k, member)
                    break

    def __setattr__(self, name: str, value: Any) -> None:
        if self.__original__:
            self._handle_origin_modification(name)

        setattr(self.__obj__, name, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__obj__, name)

    def __delattr__(self, name: str) -> None:
        return delattr(self.__obj__, name)

    def __getitem__(self, key: Any) -> Any:
        return self.__obj__[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        if self.__original__:
            self._handle_origin_modification(key)

        self.__obj__[key] = value

    def __delitem__(self, key: Any) -> None:
        if self.__original__:
            self._handle_origin_modification(key)

        del self.__obj__[key]

    def __repr__(self) -> str:
        return repr(self.__obj__)

    def __str__(self) -> str:
        return str(self.__obj__)

    def __eq__(self, value: object) -> bool:
        return self.__obj__ == value

    def __hash__(self) -> int:
        return hash(self.__obj__)

    def __deepcopy__(self, memo: Any) -> "Attachment":
        return Attachment(
            deepcopy(self.__obj__, memo),
            filename=self.__filename__,
            basename=self.__basename__,
            original=False,
        )