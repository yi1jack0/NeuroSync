"""Audio sources. Every source renders (frames, 2) float32 blocks."""
from __future__ import annotations

import wave
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from ..domain.limits import (BASE_FREQ_MAX_HZ, BASE_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ,
                             BEAT_FREQ_MIN_HZ, SAMPLE_RATE, clamp)


class AudioSource(ABC):
    @abstractmethod
    def read(self, frames: int) -> np.ndarray:
        """Return a float32 array shaped (frames, 2)."""


class OscillatorSource(AudioSource):
    """Binaural generator: left = base, right = base + beat (independent sines).

    Phase accumulators are continuous across blocks and frequency changes are
    ramped linearly within a block, so live slider moves never click.
    """

    def __init__(self, base_hz: float = 200.0, beat_hz: float = 10.0,
                 sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._base = self._target_base = clamp(base_hz, BASE_FREQ_MIN_HZ, BASE_FREQ_MAX_HZ)
        self._beat = self._target_beat = clamp(beat_hz, BEAT_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ)
        self._phase = np.zeros(2)          # radians, [left, right]

    @property
    def beat_hz(self) -> float:
        return self._target_beat

    def set_frequencies(self, base_hz: float | None = None, beat_hz: float | None = None) -> None:
        if base_hz is not None:
            self._target_base = clamp(base_hz, BASE_FREQ_MIN_HZ, BASE_FREQ_MAX_HZ)
        if beat_hz is not None:
            self._target_beat = clamp(beat_hz, BEAT_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ)

    def read(self, frames: int) -> np.ndarray:
        ramp = np.linspace(0.0, 1.0, frames, endpoint=False)
        base = self._base + (self._target_base - self._base) * ramp
        beat = self._beat + (self._target_beat - self._beat) * ramp
        self._base, self._beat = self._target_base, self._target_beat
        two_pi_over_sr = 2.0 * np.pi / self.sample_rate
        inc_l, inc_r = base * two_pi_over_sr, (base + beat) * two_pi_over_sr
        ph_l = self._phase[0] + np.cumsum(inc_l)
        ph_r = self._phase[1] + np.cumsum(inc_r)
        self._phase = np.array([ph_l[-1], ph_r[-1]]) % (2.0 * np.pi)
        out = np.empty((frames, 2), dtype=np.float32)
        out[:, 0], out[:, 1] = np.sin(ph_l), np.sin(ph_r)
        return out


class SampleSource(AudioSource):
    """Loops a stereo buffer forever. Also the base for synthetic noise beds."""

    def __init__(self, buffer: np.ndarray) -> None:
        if buffer.ndim != 2 or buffer.shape[1] != 2 or len(buffer) == 0:
            raise ValueError("buffer must be shaped (n, 2) with n > 0")
        self._buf = buffer.astype(np.float32, copy=False)
        self._pos = 0

    def read(self, frames: int) -> np.ndarray:
        n = len(self._buf)
        idx = (self._pos + np.arange(frames)) % n
        self._pos = (self._pos + frames) % n
        return self._buf[idx]

    @classmethod
    def from_file(cls, path: str | Path, sample_rate: int = SAMPLE_RATE) -> "SampleSource":
        data, rate = _load_audio(Path(path))
        if rate != sample_rate:  # linear resample; ambient beds tolerate it
            x_new = np.linspace(0, len(data) - 1, int(len(data) * sample_rate / rate))
            data = np.stack([np.interp(x_new, np.arange(len(data)), data[:, c])
                             for c in range(2)], axis=1)
        return cls(data)


def _load_audio(path: Path) -> tuple[np.ndarray, int]:
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as w:
            ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
        if width == 2:
            arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif width == 1:
            arr = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        else:
            raise ValueError("only 8/16-bit PCM wav supported without soundfile; "
                             "install neurosync[audio]")
        arr = arr.reshape(-1, ch)
    else:
        try:
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("ogg support requires: pip install neurosync[audio]") from exc
        arr, rate = sf.read(str(path), dtype="float32", always_2d=True)
        ch = arr.shape[1]
    if ch == 1:
        arr = np.repeat(arr, 2, axis=1)
    return arr[:, :2], rate


def make_noise_buffer(variant: str, seconds: float = 20.0, sample_rate: int = SAMPLE_RATE,
                      seed: int | None = None) -> np.ndarray:
    """Spectrally shaped noise. FFT synthesis is circular, so it loops seamlessly."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sample_rate)
    exponent = {"white": 0.0, "pink": 0.5, "brown": 1.0}[variant]  # amplitude ~ f^-exponent
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    freqs[0] = freqs[1]
    shape = freqs ** -exponent
    out = np.empty((n, 2), dtype=np.float32)
    for ch in range(2):  # decorrelated channels -> wide, natural stereo field
        spectrum = (rng.standard_normal(len(freqs)) + 1j * rng.standard_normal(len(freqs))) * shape
        spectrum[0] = 0.0
        sig = np.fft.irfft(spectrum, n)
        out[:, ch] = sig / (np.max(np.abs(sig)) or 1.0) * 0.7
    return out


def noise_source(variant: str, seed: int | None = None) -> SampleSource:
    return SampleSource(make_noise_buffer(variant, seed=seed))
