from typing import Literal, Optional

from pydantic import Field

from chat2edit.models.timestamped_model import TimestampedModel


class Feedback(TimestampedModel):
    severity: Literal["info", "warning", "error"]
    function: Optional[str] = Field(default=None)
