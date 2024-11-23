from dataclasses import dataclass, field
from typing import List, Optional

from chat2edit.models.error import Error
from chat2edit.models.execution import ExecutionFeedback, ExecutionResponse
from chat2edit.models.messages import ChatMessage, ContextMessage


@dataclass
class PromptingResult:
    messages: List[str] = field(default_factory=list)
    code: Optional[str] = field(default=None)
    error: Optional[Error] = field(default=None)


@dataclass
class ExecutionResult:
    blocks: List[str] = field(default_factory=list)
    feedback: Optional[ExecutionFeedback] = field(default=None)
    response: Optional[ExecutionResponse] = field(default=None)
    error: Optional[Error] = field(default=None)


@dataclass
class PromptCycle:
    prompting_result: PromptingResult
    execution_result: Optional[ExecutionResult] = field(default=None)


@dataclass
class ChatCycle:
    req_message: ChatMessage
    request: ContextMessage
    prompt_cycles: List[PromptCycle] = field(default_factory=list)
    res_message: Optional[ChatMessage] = field(default=None)
    exec_context_src: Optional[str] = field(default=None)
