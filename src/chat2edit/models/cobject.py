import inspect
from copy import deepcopy
from typing import Any, List
from uuid import uuid4

from chat2edit.utils.repr import to_snake_case


class ContextObject:
    def __init__(self, obj: Any, basename: str = "") -> None:
        self.__dict__["obj"] = obj
        self.__dict__["id"] = self._create_id()
        self.__dict__["basename"] = basename or self._create_basename()

    @property
    def __class__(self):
        return self.obj.__class__

    def _create_id(self) -> str:
        return str(uuid4())

    def _create_basename(self) -> str:
        obj_classname = type(self.obj).__name__
        return to_snake_case(obj_classname).split("_").pop()

    def __getattr__(self, name: str) -> Any:
        if hasattr(self.obj, name):
            return getattr(self.obj, name)

        return self.__dict__[name]

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self.obj, name):
            setattr(self.obj, name, value)
            return

        self.__dict__[name] = value

    def __repr__(self) -> str:
        return repr(self.obj)


class FileObjModifiedError(Exception):
    def __init__(
        self,
        varname: str,
        member: str,
    ) -> None:
        super().__init__()
        self.varname = varname
        self.member = member


class FileObject(ContextObject):
    def __init__(
        self,
        obj: Any,
        filename: str,
        basename: str = "",
        modifiable: bool = False,
        attr_paths: List[str] = [],
        query_objs: List[ContextObject] = [],
    ) -> None:
        super().__init__(obj, basename)
        self.__dict__["original"] = True
        self.__dict__["filename"] = filename
        self.__dict__["modifiable"] = modifiable
        self.__dict__["attr_paths"] = attr_paths
        self.__dict__["query_objs"] = query_objs

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "original" or not self.original or self.modifiable:
            super().__setattr__(name, value)
            return

        frame = inspect.currentframe().f_back

        for k, v in frame.f_locals.items():
            if v is self:
                raise FileObjModifiedError(k, name)

    def __deepcopy__(self, memo: Any) -> "FileObject":
        copied = FileObject(
            deepcopy(self.obj, memo),
            self.filename,
            self.basename,
            self.modifiable,
        )
        copied.original = False
        return copied
