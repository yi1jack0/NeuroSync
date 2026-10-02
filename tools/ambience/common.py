"""Shared DSP helpers for the procedural ambience generators (build-time only; needs scipy).

A generator module `gen_<id>.py` provides:
    META = dict(id, name, category, description, loop_xfade_s, duration_s,
                default_volume, order, wide=True, tonal_ok=False)
    generate(rng: np.random.Generator, sr: int) -> np.ndarray   # (n, 2) float, any scale
`finalize()` (DC removal, RMS normalise, soft limit) is applied by the build, not the generator.
"""
from __future__ import annotations

import io

import numpy as np
from scipy import signal

SR = 48_000
TARGET_RMS = 0.15      # matches the level of the generated noise beds
PEAK = 0.90            # soft-limit ceiling (the mixer's master cap sits on top of this)


# ---------------------------------------------------------------- filters (causal, SOS)
def _sos(kind: str, freq, order: int, sr: int):
    return signal.butter(order, freq, btype=kind, fs=sr, output="sos")


def lowpass(x, freq, order=4, sr=SR):
    return signal.sosfilt(_sos("lowpass", freq, order, sr), x, axis=0)


def highpass(x, freq, order=4, sr=SR):
    return signal.sosfilt(_sos("highpass", freq, order, sr), x, axis=0)


def bandpass(x, lo, hi, order=3, sr=SR):
    return signal.sosfilt(_sos("bandpass", [lo, hi], order, sr), x, axis=0)


def resonator(x, freq, q, sr=SR):
    """Narrow 2-pole band-pass (unit peak gain) - the core of bubbles / droplets / formants."""
    b, a = signal.iirpeak(freq, q, fs=sr)
    return signal.lfilter(b, a, x, axis=0)


# ---------------------------------------------------------------- noise & modulation
def white(rng, n, channels=2):
    return rng.standard_normal((n, channels)).astype(np.float64)


def colored(rng, n, exponent: float, channels=2, sr=SR):
    """FFT-shaped noise, amplitude ~ f^-exponent (0 white, 0.5 pink, 1 brown). Circular."""
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    freqs[0] = freqs[1]
    out = np.empty((n, channels))
    for c in range(channels):
        spec = (rng.standard_normal(len(freqs)) + 1j * rng.standard_normal(len(freqs))) * freqs ** -exponent
        spec[0] = 0
        out[:, c] = np.fft.irfft(spec, n)
    return out / (out.std() or 1.0)


def slow_random(rng, n, rate_hz, sr=SR, smooth=True):
    """Smooth random curve in ~[-1, 1] changing at about `rate_hz` (for envelopes / drifts)."""
    pts = max(4, int(n / sr * rate_hz * 2) + 4)
    knots = rng.standard_normal(pts)
    x = np.linspace(0, pts - 1, n)
    if smooth:
        from scipy.interpolate import CubicSpline
        y = CubicSpline(np.arange(pts), knots)(x)
    else:
        y = np.interp(x, np.arange(pts), knots)
    return y / (np.abs(y).max() or 1.0)


def envelope_unit(x):
    """Map any curve to 0..1."""
    lo, hi = x.min(), x.max()
    return (x - lo) / (hi - lo or 1.0)


def pan_gains(position: float):
    """Equal-power pan, position -1 (left) .. +1 (right) -> (gl, gr)."""
    a = (position + 1.0) * np.pi / 4.0
    return np.cos(a), np.sin(a)


def add_at(buf, start: int, grain, gl=1.0, gr=1.0):
    """Mix a mono grain into stereo buf at sample `start` (clipped at the buffer end)."""
    end = min(len(buf), start + len(grain))
    if end <= start:
        return
    g = grain[: end - start]
    buf[start:end, 0] += g * gl
    buf[start:end, 1] += g * gr


def haas_widen(x, ms=0.6, sr=SR):
    """Tiny inter-channel delay on the right channel for width without changing tone."""
    d = max(1, int(ms * sr / 1000))
    y = x.copy()
    y[d:, 1] = x[:-d, 1]
    return y


# ---------------------------------------------------------------- mastering
def finalize(x, target_rms=TARGET_RMS, peak=PEAK, sr=SR):
    """DC/sub-rumble removal -> RMS normalise -> smooth soft limit (tanh) -> re-normalise."""
    x = np.asarray(x, dtype=np.float64)
    x = signal.sosfilt(_sos("highpass", 18.0, 2, sr), x, axis=0)
    for _ in range(3):
        rms = np.sqrt(np.mean(x ** 2)) or 1.0
        x = x * (target_rms / rms)
        x = peak * np.tanh(x / peak)
    rms = np.sqrt(np.mean(x ** 2)) or 1.0
    x = x * (target_rms / rms)
    return np.clip(x, -peak, peak).astype(np.float32)


# ---------------------------------------------------------------- codec
def encode_ogg(x, sr=SR) -> bytes:
    import soundfile as sf
    buf = io.BytesIO()
    with sf.SoundFile(buf, "w", samplerate=sr, channels=2, format="OGG", subtype="VORBIS") as f:
        f.write(np.asarray(x, dtype=np.float32))
    return buf.getvalue()


def decode_ogg(raw: bytes):
    import soundfile as sf
    arr, rate = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
    return arr, rate


# ---------------------------------------------------------------- loop-aware helpers
def circular(fn, x):
    """Apply a causal filter/effect `fn` to x as if x were periodic (no warm-up transient,
    and the result's end flows into its start). Tiles x three times and keeps the middle copy."""
    n = len(x)
    return fn(np.concatenate([x, x, x]))[n:2 * n]


def add_at_circular(buf, start: int, grain, gl=1.0, gr=1.0):
    """Like add_at, but a grain that runs past the end wraps around to the start."""
    n = len(buf)
    idx = (start + np.arange(len(grain))) % n
    buf[idx, 0] += grain * gl
    buf[idx, 1] += grain * gr


def circular_random(rng, n, rate_hz, sr=SR):
    """Smooth periodic random curve in ~[-1, 1] (end meets start), varying at ~rate_hz."""
    k = max(3, int(n / sr * rate_hz))
    spec = np.zeros(n // 2 + 1, dtype=complex)
    lo, hi = 1, max(2, 2 * k)
    spec[lo:hi] = rng.standard_normal(hi - lo) + 1j * rng.standard_normal(hi - lo)
    y = np.fft.irfft(spec, n)
    return y / (np.abs(y).max() or 1.0)
