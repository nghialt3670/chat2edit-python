from abc import ABC, abstractmethod
from typing import List

from chat2edit.models.cobject import ContextObject
from chat2edit.models.error import Error
from chat2edit.models.execution import (
    ExecutionFeedback,
    FileObjModifiedFeedback,
    FunctionMessageFeedback,
    InvalidArgumentFeedback,
    Severity,
    UnassignedValueFeedback,
    UnexpectedErrorFeedback,
)


class FeedbackException(Exception, ABC):
    def __init__(self, severity: Severity) -> None:
        super().__init__()
        self.severity = severity

    @abstractmethod
    def get_feedback(self) -> ExecutionFeedback:
        pass


class InvalidArgumentException(FeedbackException):
    def __init__(
        self, func_name: str, param_name: str, param_anno: str, param_type: str
    ) -> None:
        super().__init__("error")
        self.func_name = func_name
        self.param_name = param_name
        self.param_anno = param_anno
        self.param_type = param_type

    def get_feedback(self) -> ExecutionFeedback:
        return InvalidArgumentFeedback(
            severity=self.severity,
            func_name=self.func_name,
            param_name=self.param_name,
            param_anno=self.param_anno,
            param_type=self.param_type,
        )


class FileObjModifiedException(FeedbackException):
    def __init__(self, varname: str, member: str) -> None:
        super().__init__("error")
        self.varname = varname
        self.member = member

    def get_feedback(self) -> ExecutionFeedback:
        return FileObjModifiedFeedback(self.severity, self.varname, self.member)


class FunctionMessageException(FeedbackException):
    def __init__(
        self, severity: Severity, text: str, objects: List[ContextObject]
    ) -> None:
        super().__init__(severity)
        self.text = text
        self.objects = objects

    def get_feedback(self) -> ExecutionFeedback:
        return FunctionMessageFeedback(self.severity, self.text, self.objects)


class UnassignedValueException(FeedbackException):
    def __init__(self, func_name: str, ret_anno: str) -> None:
        super().__init__("error")
        self.func_name = func_name
        self.ret_anno = ret_anno

    def get_feedback(self) -> ExecutionFeedback:
        return UnassignedValueFeedback(self.severity, self.func_name, self.ret_anno)


class UnexpectedErrorException(FeedbackException):
    def __init__(self, error: Error) -> None:
        super().__init__("error")
        self.error = error

    def get_feedback(self) -> ExecutionFeedback:
        return UnexpectedErrorFeedback(self.severity, self.error)
