from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..domain.limits import MASTER_GAIN_MAX, clamp
from .sources import AudioSource


@dataclass
class MixerChannel:
    """An AudioSource plus its live mixer state."""
    name: str
    source: AudioSource
    volume: float = 0.5
    pan: float = 0.0
    is_muted: bool = False
    is_binaural: bool = False   # binaural channels ignore pan to preserve L/R separation
    _gain: float = 0.0          # smoothed gain actually applied (click-free)

    def render(self, frames: int) -> np.ndarray:
        block = self.source.read(frames)
        target = 0.0 if self.is_muted else clamp(self.volume, 0.0, 1.0)
        ramp = np.linspace(self._gain, target, frames, endpoint=False, dtype=np.float32)
        self._gain = target
        block = block * ramp[:, None]
        if not self.is_binaural and self.pan:
            pan = clamp(self.pan, -1.0, 1.0)
            block = block * np.array([min(1.0, 1.0 - pan), min(1.0, 1.0 + pan)], dtype=np.float32)
        return block


class MixerEngine:
    """Sums channels, applies master gain (hard-capped) and a final clip guard."""

    def __init__(self) -> None:
        self.channels: list[MixerChannel] = []
        self._master = self._target_master = 0.5

    @property
    def master_volume(self) -> float:
        return self._target_master

    @master_volume.setter
    def master_volume(self, value: float) -> None:
        self._target_master = clamp(value, 0.0, MASTER_GAIN_MAX)

    def render(self, frames: int) -> np.ndarray:
        mix = np.zeros((frames, 2), dtype=np.float32)
        for ch in tuple(self.channels):  # UI swaps the list; never mutates it mid-render
            mix += ch.render(frames)
        ramp = np.linspace(self._master, self._target_master, frames, endpoint=False, dtype=np.float32)
        self._master = self._target_master
        mix *= ramp[:, None]
        np.clip(mix, -MASTER_GAIN_MAX, MASTER_GAIN_MAX, out=mix)  # never exceed 0.85 full-scale
        return mix
