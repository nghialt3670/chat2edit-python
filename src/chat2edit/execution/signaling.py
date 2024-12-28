import threading
from typing import Any, Optional

from chat2edit.constants import FEEDBACK_SIGNAL_KEY, RESPONSE_SIGNAL_KEY
from chat2edit.models import Feedback, Message


class SignalManager:
    _signals = threading.local()

    @classmethod
    def set_signal(cls, key: str, value: Any) -> None:
        setattr(SignalManager._signals, key, value)

    @classmethod
    def pop_signal(cls, key: str) -> Optional[Any]:
        if not hasattr(cls._signals, key):
            return None

        signal = getattr(cls._signals, key, None)
        delattr(cls._signals, key)

        return signal


def set_response(response: Message) -> None:
    SignalManager.set_signal(RESPONSE_SIGNAL_KEY, response)


def pop_response() -> Optional[Message]:
    return SignalManager.pop_signal(RESPONSE_SIGNAL_KEY)


def set_feedback(feedback: Feedback) -> None:
    SignalManager.set_signal(FEEDBACK_SIGNAL_KEY, feedback)


def pop_feedback() -> Optional[Feedback]:
    return SignalManager.pop_signal(FEEDBACK_SIGNAL_KEY)
