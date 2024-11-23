from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

from chat2edit.models.cobject import ContextObject
from chat2edit.models.timestamped import Timestamped
from chat2edit.utils.context import obj_to_path


@dataclass
class BaseMessage(Timestamped):
    text: str


@dataclass
class ChatMessage(BaseMessage):
    file_srcs: List[str] = field(default_factory=list)


@dataclass
class ContextMessage(BaseMessage):
    objs_or_paths: List[Union[ContextObject, str]] = field(default_factory=list)

    def convert_objs_to_paths(self, context: Dict[str, Any]) -> None:
        paths = [obj_to_path(context, obj) for obj in self.objs_or_paths]
        self.objs_or_paths = paths
