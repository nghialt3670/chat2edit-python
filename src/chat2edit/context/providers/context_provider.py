from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chat2edit.context.attachments import Attachment
from chat2edit.models import Exemplar


class ContextProvider(ABC):
    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_exemplars(self) -> List[Exemplar]:
        pass
