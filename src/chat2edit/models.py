import traceback
from itertools import chain
from time import time_ns
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from chat2edit.attachment import Attachment


class Timestamped(BaseModel):
    timestamp: int = Field(default_factory=time_ns)


class Error(Timestamped):
    message: str
    stack_trace: str

    @classmethod
    def from_exception(cls, exc: Exception) -> "Error":
        return cls(message=str(exc), stack_trace=traceback.format_exc())


class AssignedAttachment(BaseModel):
    type: str
    path: str
    attrpaths: List[str] = Field(default_factory=list)
    attachments: List["AssignedAttachment"] = Field(default_factory=list)

    def get_all_paths(self) -> List[str]:
        all_paths = []
        all_paths.append(self.path)
        all_paths.extend(self.attrpaths)
        all_paths.extend(
            chain.from_iterable(att.get_all_paths() for att in self.attachments)
        )
        return all_paths


class Message(Timestamped):
    text: str
    attachments: List[Union[Any, Attachment, AssignedAttachment]] = Field(
        default_factory=list
    )

    class Config:
        arbitrary_types_allowed = True


Severity = Literal["info", "warning", "error"]


class Feedback(Timestamped):
    severity: Severity


class Cycle(BaseModel):
    trigger: Union[Message, Feedback]
    prompts: List[str] = Field(default_factory=list)
    answers: List[str] = Field(default_factory=list)
    code: Optional[str] = Field(default=None)
    error: Optional[Error] = Field(default=None)
    blocks: List[str] = Field(default_factory=list)
    result: Optional[Union[Feedback, Message]] = Field(default=None)

    def is_request(self) -> bool:
        return isinstance(self.trigger, Message)

    def is_feedback(self) -> bool:
        return isinstance(self.trigger, Feedback) or isinstance(self.result, Feedback)

    def is_response(self) -> bool:
        return isinstance(self.result, Message)


class Phase(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)
    cycles: List[Cycle] = Field(default_factory=list)
