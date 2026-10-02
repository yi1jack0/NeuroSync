from __future__ import annotations

from enum import Enum


class BrainwaveBand(Enum):
    DELTA = ("Delta", 0.5, 4.0)
    THETA = ("Theta", 4.0, 8.0)
    ALPHA = ("Alpha", 8.0, 14.0)
    BETA = ("Beta", 14.0, 30.0)
    GAMMA = ("Gamma", 30.0, 100.0)

    def __init__(self, label: str, low_hz: float, high_hz: float) -> None:
        self.label = label
        self.low_hz = low_hz
        self.high_hz = high_hz

    @classmethod
    def for_frequency(cls, hz: float) -> "BrainwaveBand":
        for band in cls:
            if band.low_hz <= hz < band.high_hz:
                return band
        return cls.DELTA if hz < cls.DELTA.low_hz else cls.GAMMA
