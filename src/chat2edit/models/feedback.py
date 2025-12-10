from typing import Any, Dict, Literal, Optional

from pydantic import Field

from chat2edit.models.message import Message


class Feedback(Message):
    type: str  # Feedback type identifier (e.g., "invalid_parameter_type", "empty_list_parameters")
    severity: Literal["info", "warning", "error"]
    function: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default_factory=dict)  # Additional feedback-specific data
