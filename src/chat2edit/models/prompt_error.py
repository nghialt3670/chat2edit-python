import traceback
from typing import Any, Dict

from pydantic import Field

from chat2edit.models.error import Error


class PromptError(Error):
    llm: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_exception(cls, exception: Exception) -> "PromptError":
        return cls(message=str(exception), stack_trace=traceback.format_exc())
