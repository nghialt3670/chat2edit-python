import traceback
from time import time_ns
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "error"]


class Timestamped(BaseModel):
    timestamp: int = Field(default_factory=time_ns)


class Error(Timestamped):
    message: str
    stack_trace: str

    @classmethod
    def from_exception(cls, exc: Exception) -> "Error":
        return cls(message=str(exc), stack_trace=traceback.format_exc())


class Message(Timestamped):
    text: str
    attachments: List[Any] = Field(default_factory=list)


class Feedback(Timestamped):
    severity: Severity
    attachments: List[Any] = Field(default_factory=list)


class PromptExecuteLoop(BaseModel):
    prompts: List[str] = Field(default_factory=list)
    answers: List[str] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list)
    error: Optional[Error] = Field(default=None)
    feedback: Optional[Feedback] = Field(default=None)


class ChatCycle(BaseModel):
    request: Message
    response: Optional[Message] = Field(default=None)
    context: Dict[str, Any] = Field(default_factory=dict)
    loops: List[PromptExecuteLoop] = Field(default_factory=list)
