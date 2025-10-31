import inspect
from typing import Any, Callable, Optional, TypeVar

from chat2edit.context.attachments.attachment import Attachment

T = TypeVar("T")


class FileAttachment(Attachment):
    def __init__(
        self,
        obj: T,
        *,
        basename: Optional[str] = None,
        filename: Optional[str] = None,
        modifiable: bool = False,
    ) -> None:
        super().__init__(obj, basename=basename)
        self.__dict__["__filename__"] = filename
        self.__dict__["__modifiable__"] = modifiable

    @property
    def __filename__(self) -> Optional[str]:
        return self.__dict__["__filename__"]

    @property
    def __modifiable__(self) -> bool:
        return self.__dict__["__modifiable__"]

    def set_origin_modification_handler(
        self, handler: Callable[[str, str], None]
    ) -> None:
        self.__dict__["__origin_modification_handler__"] = handler

    def _handle_modification(self, member: str) -> None:
        if handler := getattr(self, "__origin_modification_handler__", None):
            caller_frame = inspect.currentframe().f_back.f_back
            for k, v in caller_frame.f_locals.items():
                if v is self:
                    handler(k, member)
                    break

    def __setattr__(self, name: str, value: Any) -> None:
        if not self.__modifiable__:
            self._handle_modification(name)

        super().__setattr__(name, value)
