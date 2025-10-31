from typing import Any, Dict

from pydantic import Field

from chat2edit.models.error import Error


class PromptError(Error):
    llm: Dict[str, Any] = Field(default_factory=dict)
