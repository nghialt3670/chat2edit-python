from typing import Any, Type, Union

from pydantic import BaseModel, TypeAdapter


class SmartTypeAdapter(TypeAdapter):
    def __init__(self, base_cls: Type[BaseModel]):
        self.base_cls = base_cls
        self.subclasses = self._get_all_subclasses()

    def _get_all_subclasses(self):
        subclasses = set()
        work = [self.base_cls]

        while work:
            parent = work.pop()

            for child in parent.__subclasses__():
                if child not in subclasses:
                    subclasses.add(child)
                    work.append(child)

        return subclasses

    def validate_python(self, obj: Any) -> BaseModel:
        if isinstance(obj, self.base_cls):
            return obj

        for subcls in self.subclasses:
            try:
                return TypeAdapter(subcls).validate_python(obj)

            except Exception:
                continue

        return TypeAdapter(self.base_cls).validate_python(obj)

    def validate_json(self, data: Union[str, bytes]) -> BaseModel:
        for subcls in self.subclasses:
            try:
                return TypeAdapter(subcls).validate_json(data)

            except Exception:
                continue

        return TypeAdapter(self.base_cls).validate_json(data)
