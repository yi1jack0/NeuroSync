from __future__ import annotations

import numpy as np

from ..domain.limits import FADE_FLOOR_DB, MIN_FADE_OUT_S, SAMPLE_RATE


class LogFade:
    """Logarithmic (linear-in-dB) fade-out, stateful across blocks.

    Gain falls 0 dB -> FADE_FLOOR_DB, with a short final taper to exact zero.
    Duration is never shorter than MIN_FADE_OUT_S.
    """

    def __init__(self, duration_s: float, sample_rate: int = SAMPLE_RATE) -> None:
        self.total = int(max(duration_s, MIN_FADE_OUT_S) * sample_rate)
        self.pos = 0

    @property
    def done(self) -> bool:
        return self.pos >= self.total

    def gains(self, frames: int) -> np.ndarray:
        t = np.minimum(self.pos + np.arange(frames), self.total) / self.total
        g = 10.0 ** (FADE_FLOOR_DB * t / 20.0)
        g *= np.clip((1.0 - t) / 0.01, 0.0, 1.0)  # last 1% tapers to true silence
        self.pos += frames
        return g.astype(np.float32)
