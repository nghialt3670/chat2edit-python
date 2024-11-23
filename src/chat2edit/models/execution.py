from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Union

from chat2edit.models.cobject import FileObject
from chat2edit.models.error import Error
from chat2edit.models.messages import BaseMessage, ContextMessage
from chat2edit.models.timestamped import Timestamped
from chat2edit.utils.context import obj_to_path

Severity = Literal["info", "warning", "error"]


@dataclass
class ExecutionFeedback(Timestamped):
    severity: Severity


@dataclass
class InvalidArgumentFeedback(ExecutionFeedback):
    func_name: str
    param_name: str
    param_anno: str
    param_type: str


@dataclass
class FunctionMessageFeedback(ContextMessage, ExecutionFeedback):
    pass


@dataclass
class FileObjModifiedFeedback(ExecutionFeedback):
    varname: str
    member: str


@dataclass
class UnassignedValueFeedback(ExecutionFeedback):
    func_name: str
    ret_anno: str


@dataclass
class UnexpectedErrorFeedback(ExecutionFeedback):
    error: Error


@dataclass
class IncompleteCycleFeedback(ExecutionFeedback):
    incomplete: bool = field(default=True)


@dataclass
class ExecutionResponse(BaseMessage):
    objs_or_paths: List[Union[FileObject, str]] = field(default_factory=list)

    def convert_objs_to_paths(self, context: Dict[str, Any]) -> None:
        paths = [obj_to_path(context, obj) for obj in self.objs_or_paths]
        self.objs_or_paths = paths
