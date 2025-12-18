from typing import List, Optional

from pydantic import Field

from chat2edit.models.execution_error import ExecutionError
from chat2edit.models.exemplary_execution_block import ExemplaryExecutionBlock


class ExecutionBlock(ExemplaryExecutionBlock):
    processed_code: str
    error: Optional[ExecutionError] = Field(default=None)
    logs: List[str] = Field(default_factory=list)
    executed: bool = Field(default=False)
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)