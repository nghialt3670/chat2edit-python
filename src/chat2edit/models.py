import traceback
from email import message
from time import time_ns
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from chat2edit.attachment import Attachment
from chat2edit.constants import (
    ATTACHMENT_MAX_ATTRIBUTE_PATHS,
    ATTACHMENT_MAX_QUERY_OBJECTS,
    CONTEXT_MAX_EXEMPLARY_CYCLES,
    MESSAGE_MAX_ATTACHMENTS,
    MESSAGE_TEXT_MAX_CHARACTERS,
    NUM_EDIT_CYCLES_PER_CHAT_CYCLE_RANGE,
)

Severity = Literal["info", "warning", "error"]


class Timestamped(BaseModel):
    timestamp: int = Field(default_factory=time_ns)


class Error(Timestamped):
    message: str
    stack_trace: str

    @classmethod
    def from_exception(cls, exc: Exception) -> "Error":
        return cls(message=str(exc), stack_trace=traceback.format_exc())


class Variable(BaseModel):
    type: str


class AssignedVariable(Variable):
    path: str


class AssignedAttachment(AssignedVariable):
    attr_paths: List[str] = Field(
        default_factory=list, max_length=ATTACHMENT_MAX_ATTRIBUTE_PATHS
    )
    query_objs: List[AssignedVariable] = Field(
        default_factory=list, max_length=ATTACHMENT_MAX_QUERY_OBJECTS
    )


class Message(Timestamped):
    text: str = Field(max_length=MESSAGE_TEXT_MAX_CHARACTERS)
    attachments: List[Union[Attachment, AssignedAttachment]] = Field(
        default_factory=list, max_length=MESSAGE_MAX_ATTACHMENTS
    )

    class Config:
        arbitrary_types_allowed = True


class PromptingResult(BaseModel):
    messages: List[str] = Field(default_factory=list)
    error: Optional[Error] = Field(default=None)
    code: Optional[str] = Field(default=None)


class Feedback(Timestamped):
    severity: Severity


class ExecutionResult(BaseModel):
    blocks: List[str] = Field(default_factory=list)
    error: Optional[Error] = Field(default=None)
    feedback: Optional[Feedback] = Field(default=None)
    response: Optional[Message] = Field(default=None)


class EditCycle(BaseModel):
    prompting_result: PromptingResult
    execution_result: ExecutionResult


class ExemplaryEditCycle(BaseModel):
    answer: str
    blocks: List[str]
    feedback_or_response: Union[Feedback, Message]


class ExemplaryChatCycle(BaseModel):
    request: Message
    edit_cycles: List[ExemplaryEditCycle]


class Context(BaseModel):
    exec_context: Dict[str, Any]
    exem_cycles: List[ExemplaryChatCycle] = Field(
        default_factory=list, max_length=CONTEXT_MAX_EXEMPLARY_CYCLES
    )


class ChatCycle(BaseModel):
    request: Message
    context: Context
    edit_cycles: List[EditCycle] = Field(
        default_factory=list, max_length=NUM_EDIT_CYCLES_PER_CHAT_CYCLE_RANGE[1]
    )

    def is_completed(self) -> bool:
        return self.edit_cycles and self.edit_cycles[-1].execution_result.response
