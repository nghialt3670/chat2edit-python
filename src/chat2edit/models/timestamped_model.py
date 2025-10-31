from time import time_ns

from pydantic import BaseModel, Field


class TimestampedModel(BaseModel):
    timestamp: int = Field(default_factory=time_ns)
