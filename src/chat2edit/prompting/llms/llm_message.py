from chat2edit.models.timestamped_model import TimestampedModel


class LlmMessage(TimestampedModel):
    text: str
