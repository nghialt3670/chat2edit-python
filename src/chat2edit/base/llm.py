from abc import ABC, abstractmethod
from typing import List


class Llm(ABC):
    @abstractmethod
    async def generate(self, messages: List[str]) -> str:
        pass
