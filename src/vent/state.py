from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    PAUSED = auto()
    TRANSCRIBING = auto()
