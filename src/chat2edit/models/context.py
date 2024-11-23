from dataclasses import dataclass
from typing import Any, Dict, List

from chat2edit.models.cycles import ChatCycle


@dataclass
class Context:
    exec_context: Dict[str, Any]
    exem_cycles: List[ChatCycle]
