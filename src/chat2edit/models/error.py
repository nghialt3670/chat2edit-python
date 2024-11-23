import traceback
from dataclasses import dataclass

from chat2edit.models.timestamped import Timestamped


@dataclass
class Error(Timestamped):
    message: str
    stack_trace: str

    @classmethod
    def from_exception(cls, exception: Exception) -> "Error":
        return cls(message=str(exception), stack_trace=traceback.format_exc())
