from abc import ABC, abstractmethod

from chat2edit.models.file import File


class FileStorage(ABC):
    @abstractmethod
    async def load(self, src: str) -> File:
        pass

    @abstractmethod
    async def save(self, file: File) -> str:
        pass
