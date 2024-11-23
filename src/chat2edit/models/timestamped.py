from dataclasses import dataclass, field
from time import time_ns


@dataclass
class Timestamped:
    timestamp: int = field(init=False, repr=False)

    def __post_init__(self):
        self.timestamp = time_ns()
