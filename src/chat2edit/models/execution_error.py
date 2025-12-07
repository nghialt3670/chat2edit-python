import traceback
from typing import Optional

from pydantic import Field

from chat2edit.models.error import Error


class ExecutionError(Error):
    function: Optional[str] = Field(default=None)

    @classmethod
    def from_exception(cls, exception: Exception) -> "ExecutionError":
        return cls(message=str(exception), stack_trace=traceback.format_exc())
