from __future__ import annotations

import enum
from typing import Callable

import numpy as np

from ..domain.limits import SAMPLE_RATE
from ..domain.models import Preset
from ..engine.fade import LogFade
from ..engine.mixer import MixerEngine
from .builder import AudioGraphBuilder


class SessionState(enum.Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FADING = "fading"
    STOPPED = "stopped"


class Session:
    """Runtime state built from a Preset: lifecycle, countdown timer, fade-out.

    Time is measured in rendered frames (not wall clock), so the timer stays in
    lock-step with the audio and is fully deterministic under test.
    """

    def __init__(self, preset: Preset, master_volume: float = 0.5,
                 sample_rate: int = SAMPLE_RATE,
                 on_finished: Callable[[], None] | None = None) -> None:
        self.preset = preset
        self.sample_rate = sample_rate
        self.mixer: MixerEngine = AudioGraphBuilder().build(preset, master_volume)
        self.state = SessionState.IDLE
        self.on_finished = on_finished
        self._fade: LogFade | None = None
        self._timer_frames: int | None = None
        self._fade_s = 0.0
        self._frames_played = 0

    # --- controls -----------------------------------------------------
    def set_timer(self, minutes: float | None, fade_minutes: float = 0.0) -> None:
        self._timer_frames = None if minutes is None else int(minutes * 60 * self.sample_rate)
        self._fade_s = fade_minutes * 60
        self._frames_played = 0

    def play(self) -> None:
        if self.state in (SessionState.IDLE, SessionState.PAUSED, SessionState.STOPPED):
            self._fade = None
            self.state = SessionState.PLAYING

    def pause(self) -> None:
        if self.state is SessionState.PLAYING:
            self.state = SessionState.PAUSED

    def stop(self, fade_s: float = 3.0) -> None:
        """Begin a fade-out (min 3 s enforced); never cuts abruptly."""
        if self.state in (SessionState.PLAYING, SessionState.PAUSED):
            self._fade = LogFade(fade_s, self.sample_rate)
            self.state = SessionState.FADING

    @property
    def remaining_s(self) -> float | None:
        if self._timer_frames is None:
            return None
        return max(0.0, (self._timer_frames - self._frames_played) / self.sample_rate)

    # --- audio callback -------------------------------------------------
    def render(self, frames: int) -> np.ndarray:
        if self.state in (SessionState.IDLE, SessionState.PAUSED, SessionState.STOPPED):
            return np.zeros((frames, 2), dtype=np.float32)

        block = self.mixer.render(frames)

        if self.state is SessionState.PLAYING and self._timer_frames is not None:
            self._frames_played += frames
            fade_frames = int(self._fade_s * self.sample_rate)
            if self._frames_played >= self._timer_frames - fade_frames:
                # Timer fade begins now; if fade is 0 the 3 s minimum still applies.
                self._fade = LogFade(max(self._fade_s, 0.0), self.sample_rate)
                self._fade.pos = max(0, self._frames_played - (self._timer_frames - fade_frames))
                self.state = SessionState.FADING

        if self.state is SessionState.FADING and self._fade is not None:
            block = block * self._fade.gains(frames)[:, None]
            if self._fade.done:
                self.state = SessionState.STOPPED
                if self.on_finished:
                    self.on_finished()
        return block
