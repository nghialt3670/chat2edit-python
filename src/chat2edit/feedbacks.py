from pydantic import BaseModel, Field

from chat2edit.models import Error, Feedback, Message, Severity


class Parameter(BaseModel):
    name: str
    anno: str
    type: str


class InvalidArgumentFeedback(Feedback):
    severity: Severity = Field(default="error")
    param: Parameter


class FunctionMessageFeedback(Message, Feedback):
    pass


class FileObjModifiedFeedback(Feedback):
    varname: str
    member: str


class UnassignedValueFeedback(Feedback):
    func: str
    rtype: str


class UnexpectedErrorFeedback(Feedback):
    severity: Severity = Field(default="error")
    error: Error


class IncompleteCycleFeedback(Feedback):
    severity: Severity = Field(default="info")
    incomplete: bool = Field(default=True)
