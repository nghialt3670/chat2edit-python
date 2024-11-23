import pickle
from typing import Any


def is_pickleable(value: Any) -> bool:
    try:
        pickle.dumps(value)
        return True
    except:
        return False
