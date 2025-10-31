import traceback

from chat2edit.models.timestamped_model import TimestampedModel


class Error(TimestampedModel):
    message: str
    stack_trace: str

    @classmethod
    def from_exception(cls, exception: Exception) -> "Error":
        return cls(message=str(exception), stack_trace=traceback.format_exc())
