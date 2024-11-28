import threading
from typing import Any, Optional

__all__ = ["set_signal", "check_signal", "get_signal", "clear_signal"]


class SignalManager:
    _signals = threading.local()

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        setattr(SignalManager._signals, key, value)

    @classmethod
    def check(cls, key: str) -> bool:
        return cls.get(key) is not None

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        return getattr(cls._signals, key, None)

    @classmethod
    def clear(cls, key: str) -> None:
        delattr(cls._signals, key)


def set_signal(key: str, value: Any) -> None:
    SignalManager.set(key, value)


def check_signal(key: str) -> bool:
    return SignalManager.check(key)


def get_signal(key: str) -> Optional[Any]:
    return SignalManager.get(key)


def clear_signal(key: str) -> None:
    SignalManager.clear(key)
