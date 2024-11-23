from abc import ABC, abstractmethod

from chat2edit.models.cobject import FileObject
from chat2edit.models.context import Context
from chat2edit.models.file import File


class ContextProvider(ABC):
    @abstractmethod
    def get_context(self) -> Context:
        pass

    @abstractmethod
    def load_file_obj(self, file: File) -> FileObject:
        pass

    @abstractmethod
    def save_file_obj(self, obj: FileObject) -> File:
        pass
