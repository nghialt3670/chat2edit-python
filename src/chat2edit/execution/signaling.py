import threading
from typing import Optional

from chat2edit.constants import (
    EXECUTION_FEEDBACK_SIGNAL_KEY,
    EXECUTION_RESPONSE_SIGNAL_KEY,
)
from chat2edit.models.execution import ExecutionFeedback
from chat2edit.models.messages import ContextMessage


class SignalManager:
    _signals = threading.local()

    @classmethod
    def signal_response(cls, response: ContextMessage):
        setattr(SignalManager._signals, EXECUTION_RESPONSE_SIGNAL_KEY, response)

    @classmethod
    def check_response(cls) -> bool:
        return cls.get_response() is not None

    @classmethod
    def get_response(cls) -> Optional[ContextMessage]:
        return getattr(cls._signals, EXECUTION_RESPONSE_SIGNAL_KEY, None)

    @classmethod
    def signal_feedback(cls, feedback: ExecutionFeedback):
        setattr(cls._signals, EXECUTION_FEEDBACK_SIGNAL_KEY, feedback)

    @classmethod
    def check_feedback(cls) -> bool:
        return cls.get_feedback() is not None

    @classmethod
    def get_feedback(cls) -> Optional[ExecutionFeedback]:
        return getattr(cls._signals, EXECUTION_FEEDBACK_SIGNAL_KEY, None)

    @classmethod
    def clear_signals(cls) -> None:
        cls._signals = threading.local()
