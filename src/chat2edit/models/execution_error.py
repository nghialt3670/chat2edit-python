from typing import Optional

from pydantic import Field

from chat2edit.models.error import Error


class ExecutionError(Error):
    function: Optional[str] = Field(default=None)
