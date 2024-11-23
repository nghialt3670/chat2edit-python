import mimetypes
import os
from typing import Any, Coroutine

from chat2edit.base import FileStorage
from chat2edit.models import File


class SystemFileStorage(FileStorage):
    def __init__(self, save_dir: str) -> None:
        super().__init__()
        self.save_dir = save_dir

    async def load(self, src: str) -> Coroutine[Any, Any, File]:
        filename = src.split("/").pop()
        mimetype = mimetypes.guess_type(src)[0] or ""

        with open(src, "rb") as f:
            buffer = f.read()

        return File(mimetype=mimetype, filename=filename, buffer=buffer)

    async def save(self, file: File) -> Coroutine[Any, Any, str]:
        os.makedirs(self.save_dir, exist_ok=True)
        filepath = os.path.join(self.save_dir, file.filename)

        with open(filepath, "wb") as f:
            f.write(file.buffer)

        return filepath
