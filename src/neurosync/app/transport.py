"""Owns the active Session and everything the UI does to it while audio runs.

- swapping presets crossfades (no pop between sessions)
- pause/resume ramps the output instead of cutting it
- live channel edits keep the draft Preset and the running mixer in sync
- runs without audio hardware: `render()` can be driven by any player
"""
from __future__ import annotations

import copy
from typing import Callable

import numpy as np

from ..domain.limits import SAMPLE_RATE
from ..domain.models import BINAURAL, ChannelConfig, Preset
from ..engine.sources import OscillatorSource
from .builder import AudioGraphBuilder
from .session import Session, SessionState

CROSSFADE_S = 0.35
PAUSE_RAMP_S = 0.12


class Transport:
    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self.session: Session | None = None
        self.draft: Preset | None = None          # what the mixer currently shows
        self._outgoing: Session | None = None
        self._xfade_pos = 0
        self._duck = 1.0                          # pause/resume ramp gain
        self._duck_target = 1.0
        self._master = 0.5
        self._timer: tuple[float | None, float] = (None, 0.0)
        self._builder = AudioGraphBuilder()
        self.dirty = False                        # draft differs from its source preset

    # --- state -----------------------------------------------------------
    @property
    def state(self) -> SessionState:
        if self.session is None:
            return SessionState.IDLE
        if self._duck_target == 0.0 and self.session.state is SessionState.PLAYING:
            return SessionState.PAUSED            # ramping down toward pause
        return self.session.state

    @property
    def is_playing(self) -> bool:
        return self.state in (SessionState.PLAYING, SessionState.FADING)

    @property
    def remaining_s(self) -> float | None:
        return self.session.remaining_s if self.session else None

    @property
    def beat_hz(self) -> float | None:
        if self.session:
            for ch in self.session.mixer.channels:
                if isinstance(ch.source, OscillatorSource) and not ch.is_muted:
                    return ch.source.beat_hz
        return None

    # --- preset loading -----------------------------------------------------
    def load(self, preset: Preset) -> None:
        was_playing = self.is_playing
        self.draft = copy.deepcopy(preset)
        self.dirty = False
        new = Session(self.draft, master_volume=self._master, sample_rate=self.sample_rate)
        new.set_timer(*self._timer)
        if was_playing and self.session is not None:
            self._outgoing, self._xfade_pos = self.session, 0
            new.play()
        self.session = new

    # --- transport controls ------------------------------------------------
    def play(self) -> None:
        if self.session is None:
            return
        if self.session.state is SessionState.STOPPED:
            self.session = Session(self.draft, master_volume=self._master,
                                   sample_rate=self.sample_rate)
            self.session.set_timer(*self._timer)
        self._duck_target = 1.0
        self.session.play()

    def pause(self) -> None:
        if self.session and self.session.state is SessionState.PLAYING:
            self._duck_target = 0.0               # render() pauses once ramp hits 0

    def toggle(self) -> None:
        self.pause() if self.state is SessionState.PLAYING else self.play()

    def stop(self) -> None:
        if self.session is None:
            return
        if self._duck_target == 0.0:              # paused or pausing: nothing audible to fade
            self.session.state = SessionState.STOPPED
            self._duck_target = self._duck = 1.0
            return
        self.session.stop()

    def set_master(self, value: float) -> None:
        self._master = value
        for s in (self.session, self._outgoing):
            if s:
                s.mixer.master_volume = value

    @property
    def master(self) -> float:
        return self.session.mixer.master_volume if self.session else self._master

    def set_timer(self, minutes: float | None, fade_minutes: float) -> None:
        self._timer = (minutes or None, fade_minutes)
        if self.session:
            self.session.set_timer(minutes or None, fade_minutes)

    # --- live channel editing -------------------------------------------------
    def update_channel(self, index: int, **changes) -> None:
        cfg = self.draft.channels[index]
        for k, v in changes.items():
            setattr(cfg, k, v)
        cfg.__post_init__()                       # re-apply safety clamps
        live = self.session.mixer.channels[index]
        live.volume, live.pan, live.is_muted = cfg.volume, cfg.pan, cfg.muted
        if cfg.kind == BINAURAL:
            live.source.set_frequencies(cfg.base_hz, cfg.beat_hz)
        self.dirty = True

    def add_channel(self, cfg: ChannelConfig) -> None:
        ch = self._builder.build_channel(cfg)   # may raise (bad file) before touching state
        self.draft.channels.append(cfg)
        self.session.mixer.channels = [*self.session.mixer.channels, ch]
        self.dirty = True

    def remove_channel(self, index: int) -> None:
        del self.draft.channels[index]
        chans = list(self.session.mixer.channels)
        del chans[index]
        self.session.mixer.channels = chans
        self.dirty = True

    # --- audio callback -----------------------------------------------------------
    def render(self, frames: int) -> np.ndarray:
        if self.session is None:
            return np.zeros((frames, 2), dtype=np.float32)
        block = self.session.render(frames)

        if self._outgoing is not None:
            total = int(CROSSFADE_S * self.sample_rate)
            t = (self._xfade_pos + np.arange(frames)) / total
            fade_in = np.clip(t, 0.0, 1.0).astype(np.float32)[:, None]
            out = self._outgoing.render(frames)
            block = block * np.sqrt(fade_in) + out * np.sqrt(1.0 - fade_in)  # equal power
            self._xfade_pos += frames
            if self._xfade_pos >= total:
                self._outgoing = None

        if self._duck != 1.0 or self._duck_target != 1.0:
            step = frames / (PAUSE_RAMP_S * self.sample_rate)
            end = (min(self._duck + step, 1.0) if self._duck_target > self._duck
                   else max(self._duck - step, 0.0))
            block = block * np.linspace(self._duck, end, frames, dtype=np.float32)[:, None]
            self._duck = end
            if end == 0.0 and self._duck_target == 0.0:
                self.session.pause()
        return block
