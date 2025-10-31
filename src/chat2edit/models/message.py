from chat2edit.models.timestamped_model import TimestampedModel


class Message(TimestampedModel):
    text: str
