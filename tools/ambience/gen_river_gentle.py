"""Gentle River: a calm, shallow brook babbling over smooth stones.

Model (all circular so the 30 s file loops without a seam):
  1. water bed   - band-limited noise (~300 Hz..~13 kHz, gently tilted, with an airy top) split into
                   a few bands that breathe independently (slow, uneven + a faint fast 'burble')
  2. babble      - hundreds of Minnaert-style bubbles per second: exponentially decaying sines (each
                   rings for ~2-10 ms) whose pitch glides up 5-30 % over about the decay time
                   (f ~ 3.26 / r), four radius populations whose rate falls smoothly with pitch
                   (large = rare and low ... tiny = bright sparkle), Poisson timing with a slowly
                   varying rate, log-normal amplitudes, equal-power pan + inter-channel phase
                   decorrelation
  3. body        - faint, low flow rumble under ~300 Hz
"""
from __future__ import annotations

import numpy as np
from scipy import special

import common

META = dict(
    id="river-gentle",
    name="Gentle River",
    category="Water",
    description="A calm, shallow river babbling softly over smooth stones.",
    loop_xfade_s=2.5,
    duration_s=30,
    default_volume=0.42,   # bright bed reads ~2 dB louder than the dark ones at equal RMS
    order=1,
    wide=True,
    tonal_ok=False,
)


# ------------------------------------------------------------------ helpers
def _fft_shape(white, sr, shape_fn):
    """Circular (periodic) filtering of (n, ch) noise by a magnitude response f(freq)."""
    n = len(white)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    h = shape_fn(np.maximum(f, 1e-3))
    h[0] = 0.0
    return np.fft.irfft(np.fft.rfft(white, axis=0) * h[:, None], n, axis=0)


def _band_resp(f, lo, hi, order_lo=4, order_hi=4):
    return (1.0 / np.sqrt(1.0 + (lo / f) ** (2 * order_lo))) / np.sqrt(1.0 + (f / hi) ** (2 * order_hi))


def _positive_mod(rng, n, sr, slow_hz, fast_hz, slow_depth, fast_depth):
    """Circular, always-positive gain curve: 1 + slow (uneven breathing) + fast (burble)."""
    m = 1.0 + slow_depth * common.circular_random(rng, n, slow_hz, sr) \
        + fast_depth * common.circular_random(rng, n, fast_hz, sr)
    return np.maximum(m, 0.15)


BED_TILT = 0.08
BED_TOP_HZ = 10000.0


# ------------------------------------------------------------------ layers
def _bed(rng, n, sr):
    white = common.white(rng, n)
    # a small common component keeps the width natural but mono-safe (L/R stay balanced)
    white = 0.94 * white + 0.34 * common.white(rng, n, 1)
    edges = [300, 520, 900, 1500, 2600, 4300, 7000, 10500, 15000]
    out = np.zeros((n, 2))
    for lo, hi in zip(edges[:-1], edges[1:]):
        band = _fft_shape(white, sr, lambda f, lo=lo, hi=hi: _band_resp(f, lo, hi, 3, 3))
        band /= band.std()
        centre = np.sqrt(lo * hi)
        for c in range(2):
            g = _positive_mod(rng, n, sr, 0.35, 6.0 + 3.0 * rng.random(), 0.30, 0.18)
            # slightly rising per-band gain: the airy top (7-15 kHz) is a soft shimmer, not a hiss
            out[:, c] += band[:, c] * g * (centre / 1000.0) ** BED_TILT * np.sqrt(hi - lo) / 40.0
    # gentle overall shaping so the very top rolls off softly (well above the 7 kHz of the old bed)
    out = _fft_shape(out, sr, lambda f: _band_resp(f, 300, BED_TOP_HZ, 3, 3))
    return out / out.std()


def _body(rng, n, sr):
    low = _fft_shape(common.white(rng, n), sr, lambda f: _band_resp(f, 60, 260, 2, 3))
    low /= low.std()
    g = _positive_mod(rng, n, sr, 0.25, 0.9, 0.35, 0.15)
    return low * g[:, None]


# Bubble radius populations, a monotone size distribution: the rate falls smoothly as the bubbles get
# smaller / brighter ('small bubbles rarer and brighter'), but even the tiny ones still ring for ~2 ms
# so they read as sparkle instead of clicks (energy per bubble ~ amp^2 * tau, so amp is raised to match).
POPS = [  # (name, rate /s, f median Hz, f spread (ln), Q median, amp)
    ("large", 60.0, 500.0, 0.45, 14.0, 0.26),    # large, rare, low 'gloops'
    ("main", 260.0, 1600.0, 0.45, 18.0, 0.55),   # main babble
    ("small", 150.0, 3400.0, 0.38, 25.0, 0.62),  # small, bright
    ("tiny", 70.0, 5500.0, 0.38, 35.0, 0.72),    # tiny droplets, airy sparkle
]
ZMAX = 3.0   # log-normal pitch spread is truncated at +-3 sigma (not clipped: a hard clip piles events up
#              at the range edge and makes a steady, audible whistle at that pitch)


def _shared(rng, n, sr):
    """Burble clusters shared by all populations (water tumbling over a stone splashes at all pitches)."""
    return 0.30 * common.circular_random(rng, n, 0.40, sr) + 0.22 * common.circular_random(rng, n, 3.0, sr) \
        + 0.15 * common.circular_random(rng, n, 8.0, sr)


def _population(rng, n, sr, dur, spec, shared):
    """Random parameters (timing, pitch, decay, glide, level, pan) for one bubble population."""
    _, rate, fmed, fsig, qmed, pamp = spec
    tgrid = np.arange(n) / sr
    # inhomogeneous Poisson process: slowly varying, circular rate
    r = np.exp(shared + 0.40 * common.circular_random(rng, n, 0.45, sr) + 0.20 * common.circular_random(rng, n, 2.5, sr))
    cdf = np.cumsum(r)
    cdf /= cdf[-1]
    cnt = rng.poisson(rate * dur)
    t0 = np.interp(rng.random(cnt), cdf, tgrid)
    starts = (t0 * sr).astype(np.int64)

    zlo, zhi = special.ndtr(-ZMAX), special.ndtr(ZMAX)
    f0 = fmed * np.exp(fsig * special.ndtri(rng.uniform(zlo, zhi, cnt)))
    # a bubble rings for several tens of cycles (~2-10 ms), long enough to hear as a 'plink'
    q = qmed * np.exp(np.clip(0.25 * rng.standard_normal(cnt), -0.5, 0.35))   # no very long, whistle-like rings
    tau = q / (np.pi * f0)                                  # amplitude decay time (s)
    # pitch glides up by 5-30 %, with a sweep time ~ the decay time, so the rising chirp spans the
    # audible ring instead of being over in the first cycles
    glide = np.exp(rng.uniform(np.log(0.05), np.log(0.30), cnt)) * (rng.random(cnt) > 0.10)
    tau_g = np.clip(tau * rng.uniform(0.6, 1.6, cnt), 2.0e-3, 25e-3)
    amp = np.minimum(np.exp(0.7 * rng.standard_normal(cnt)), 3.0) * (f0 / 1500.0) ** -0.15 * pamp
    pos = np.tanh(1.5 * rng.standard_normal(cnt))
    gl, gr = common.pan_gains(pos)
    return dict(starts=starts, f0=f0, tau=tau, glide=glide, tau_g=tau_g, amp=amp, gl=gl, gr=gr,
                dphi=rng.uniform(-1, 1, cnt) * np.pi * 0.7, phi0=rng.uniform(0, 2 * np.pi, cnt))


def _bubbles(rng, n, sr, dur):
    """Vectorised Minnaert bubble synthesis, overlap-added circularly."""
    out = np.zeros((n, 2))
    shared = _shared(rng, n, sr)
    for spec in POPS:
        P = _population(rng, n, sr, dur, spec, shared)
        starts, f0, tau, glide, tau_g, amp = (P[k] for k in ("starts", "f0", "tau", "glide", "tau_g", "amp"))
        gl, gr, dphi, phi0 = P["gl"], P["gr"], P["dphi"], P["phi0"]
        order = np.argsort(tau)
        B = 700
        for i in range(0, len(f0), B):
            ids = order[i:i + B]
            L = int(np.ceil(7.5 * tau[ids].max() * sr)) + 8
            t = (np.arange(L) / sr)[None, :]
            ff = f0[ids, None] * (1.0 + glide[ids, None] * (1.0 - np.exp(-t / tau_g[ids, None])))
            ph = 2 * np.pi * np.cumsum(ff, axis=1) / sr + phi0[ids, None]
            env = np.exp(-t / tau[ids, None]) * (1.0 - np.exp(-t / 2.5e-4)) * amp[ids, None]
            gL = np.sin(ph) * env
            gR = np.sin(ph + dphi[ids, None]) * env
            idx = (starts[ids, None] + np.arange(L)[None, :]) % n
            flat = idx.ravel()
            out[:, 0] += np.bincount(flat, (gL * gl[ids, None]).ravel(), minlength=n)
            out[:, 1] += np.bincount(flat, (gR * gr[ids, None]).ravel(), minlength=n)
    # keep the babble above the 'body' region (bubble skirts would otherwise smear into the low end)
    return _fft_shape(out, sr, lambda f: 1.0 / np.sqrt(1.0 + (330.0 / f) ** 6))


# ------------------------------------------------------------------ entry point
def generate(rng, sr):
    dur = META["duration_s"]
    n = int(dur * sr)
    bed = _bed(rng, n, sr)
    bub = _bubbles(rng, n, sr, dur)
    bub /= bub.std()
    body = _body(rng, n, sr)
    return 0.40 * bed + 1.0 * bub + 0.07 * body
