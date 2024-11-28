from typing import Optional

from chat2edit.constants import FEEDBACK_SIGNAL_KEY, RESPONSE_SIGNAL_KEY
from chat2edit.models import Feedback, Message
from chat2edit.utils.signaling import check_signal, clear_signal, get_signal, set_signal


def set_response(response: Message) -> None:
    set_signal(RESPONSE_SIGNAL_KEY, response)


def check_response() -> bool:
    return check_signal(RESPONSE_SIGNAL_KEY)


def get_response() -> Optional[Message]:
    return get_signal(RESPONSE_SIGNAL_KEY)


def clear_response() -> None:
    clear_signal(RESPONSE_SIGNAL_KEY)


def set_feedback(feedback: Feedback) -> None:
    set_signal(FEEDBACK_SIGNAL_KEY, feedback)


def check_feedback() -> bool:
    return check_signal(FEEDBACK_SIGNAL_KEY)


def get_feedback() -> Optional[Feedback]:
    return get_signal(FEEDBACK_SIGNAL_KEY)


def clear_feedback() -> None:
    clear_signal(FEEDBACK_SIGNAL_KEY)
