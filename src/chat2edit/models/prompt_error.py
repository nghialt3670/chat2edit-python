from typing import Any, Dict

from chat2edit.models.error import Error


class PromptError(Error):
    llm: Dict[str, Any]
