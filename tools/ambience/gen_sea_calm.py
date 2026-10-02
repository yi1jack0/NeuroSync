"""Peaceful Sea Waves: slow, gentle waves washing onto a quiet sandy shore.

The loop the app really plays is duration_s - loop_xfade_s long (the tail is crossfaded into the head),
so the wave envelopes repeat with that period (33 s): head and tail of the file carry the same
envelope (but independent noise), the crossfade is level-neutral and the spacing the listener hears
is exactly the spacing designed here. Noise is shaped periodically (FFT) and grains wrap around.

Three waves per loop arrive ~8-12.5 s apart (clearly jittered spacing, one big / one medium / one small
wave in random order, two of the three trailed by a small second run-up that shows as a shoulder on
the retreat). The wash level and the swell also surge slowly and irregularly (~1 Hz random, periodic
over the loop) so the inside of each wave is never a smooth hump. One wave is three coupled envelopes:
  * swell   - low-mid rumble (80-500 Hz) that builds over ~3-4 s and peaks just before the crest
  * wash    - broadband noise through a time-varying low-pass: the cut-off opens with the wave
              (dark swell -> 1-3 kHz crest with a little fizz to ~8 kHz) and closes again as it
              retreats over 4-5 s
  * foam    - a soft sizzle that sits at 1.5-4 kHz and rolls off above (4-8 kHz is only a fine fizz
              carried by rare high pops, like real foam). It is a dense but heavy-tailed train of
              tiny bubble pops (uneven sizes, loose random bursts, a faint hiss underneath), so
              single pops stay audible as a crackle from the crest onward; it peaks right after the
              crest and drains away slowly (the bubbles get fewer, lower and quieter as it thins)
Under it all runs a quiet, slowly breathing distant-sea bed, so the water never goes silent.
The wash sweeps slightly left/right with each wave; channels are independent noise (decorrelated).
"""
from __future__ import annotations

import numpy as np

import common

META = dict(
    id="sea-calm",
    name="Peaceful Sea Waves",
    category="Water",
    description="Slow, gentle waves washing onto a quiet sandy shore.",
    loop_xfade_s=3.0,
    duration_s=36,
    default_volume=0.5,
    order=3,
    wide=True,
    tonal_ok=False,
)


# foam / mix tuning (module constants, so a scratch script can sweep them)
HISS_GAIN = 0.20
CLUSTER = 0.6
POP_RATE_A = 4800.0
POP_RATE_B = 300.0
POP_SIGMA = 0.85
FOAM_KNEE = 2600.0
FOAM_MIX = 0.75
BED_MIX = 0.90


# ------------------------------------------------------------------ helpers
def _fft_shape(x, sr, fn):
    """Periodic (zero-phase, no warm-up) filtering of (n, ch) noise by a magnitude response fn(f)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    h = fn(np.maximum(f, 1e-3))
    h[0] = 0.0
    return np.fft.irfft(np.fft.rfft(x, axis=0) * h[:, None], n, axis=0)


def _band(f, lo, hi, order_lo=3, order_hi=3):
    return (1.0 / np.sqrt(1.0 + (lo / f) ** (2 * order_lo))) / np.sqrt(1.0 + (f / hi) ** (2 * order_hi))


def _cmod(rng, n, dur, rate_hz, depth, floor=0.2):
    """Periodic, always-positive gain 1 + depth * smooth random (built at 400 Hz, then interpolated)."""
    sr_s = 400
    ns = int(dur * sr_s)
    y = common.circular_random(rng, ns, rate_hz, sr_s)
    xp = np.arange(ns + 1)
    x = np.arange(n) * (ns / n)
    g = np.interp(x, xp, np.append(y, y[0]))
    return np.maximum(1.0 + depth * g, floor)


def _circ_u(t, tc, dur):
    """Signed circular time (s) of t relative to tc, in [-dur/2, dur/2)."""
    return (t - tc + dur / 2.0) % dur - dur / 2.0


def _rise(x):
    x = np.clip(x, 0.0, 1.0)
    return np.sin(0.5 * np.pi * x) ** 2


def _wave_env(u, tr, tf, k=0.46, pw=1.6):
    """Asymmetric wave: smooth swell over tr s up to u=0 (soft crest), then a long smooth retreat
    (quick at first, then a slowly thinning tail) that is gone after tf s."""
    y = np.clip(u / tf, 0.0, 1.0)
    f1 = np.exp(-(1.0 / k) ** pw)
    fall = np.maximum((np.exp(-(y / k) ** pw) - f1) / (1.0 - f1), 0.0)
    return np.where(u < 0.0, _rise((u + tr) / tr), fall)


# ------------------------------------------------------------------ wave layout
def _waves(rng, period):
    """Three waves of clearly different size (two of them with a small second run-up) on a circle of
    `period` s = the length the app really loops (file length minus the crossfade), so the spacing the
    listener hears is the spacing designed here. Sizes and run-up subset are drawn as permutations,
    not independent coin flips, so every seed has a big, a medium and a small wave."""
    k = 3
    for _ in range(200):                              # clearly jittered, but still ~8-12.5 s apart
        gaps = rng.uniform(0.74, 1.26, k)
        gaps *= period / gaps.sum()
        if gaps.min() >= 8.2 and gaps.max() <= 12.6:
            break
    start = 0.17 * period + rng.uniform(-0.8, 0.8)
    crest = start + np.concatenate([[0.0], np.cumsum(gaps[:-1])])
    h = np.array([rng.uniform(0.84, 0.92), rng.uniform(0.62, 0.72), rng.uniform(0.36, 0.42)])[rng.permutation(k)]
    runups = set(rng.permutation(k)[:2].tolist())
    out = []
    for i in range(k):
        d = rng.choice([-1.0, 1.0])
        out.append(dict(tc=crest[i] % period, h=h[i], tr=rng.uniform(2.7, 4.4), tf=rng.uniform(4.3, 6.4), dir=d))
        if i in runups:                               # a second, smaller run-up on the retreating water
            out.append(dict(tc=(crest[i] + rng.uniform(3.0, 4.0)) % period,
                            h=min(rng.uniform(0.28, 0.40), 0.62 * h[i]),
                            tr=rng.uniform(1.8, 2.6), tf=rng.uniform(3.2, 4.2), dir=d))
    return out


def _surge(rng, n, sr, period, depth=0.25):
    """Slow irregular surging of the water (~1 Hz random, about +-2 dB at its peaks), periodic over the
    loop period so head and tail of the file carry the same surge; tiled up to the file length n."""
    m = int(round(period * sr))
    g = common.circular_random(rng, m, rng.uniform(0.8, 1.5), sr)
    return 1.0 + depth * g[np.arange(n) % m]


def _tracks(waves, n, sr, period):
    t = (np.arange(n) / sr) % period      # envelopes repeat every `period`: head and tail of the file match
    aw = np.zeros(n)      # wash amplitude
    br = np.zeros(n)      # wash brightness (opens with the wave, closes faster than the level falls)
    sw = np.zeros(n)      # swell rumble
    fo = np.zeros(n)      # foam
    pn = np.zeros(n)
    wsum = np.full(n, 0.35)
    for w in waves:
        u = _circ_u(t, w["tc"], period)
        e = _wave_env(u, w["tr"], w["tf"])
        aw += w["h"] * e
        br += w["h"] * _wave_env(u, w["tr"] * 0.95, w["tf"] * 0.62)
        sw += w["h"] * _wave_env(u + 0.4, w["tr"] * 1.25, w["tf"] * 0.7)
        fo += w["h"] * _wave_env(u - 1.0, 1.9, w["tf"] * 1.5, 0.5, 1.25)
        s = np.clip((u + w["tr"]) / (w["tr"] + w["tf"]), 0.0, 1.0)
        s = s * s * (3.0 - 2.0 * s)
        pn += w["h"] * e * w["dir"] * 0.70 * (2.0 * s - 1.0)
        wsum += w["h"] * e
    return t, aw, br, sw, fo, pn / wsum


# ------------------------------------------------------------------ layers
def _bed(rng, n, sr, dur):
    """Distant sea: dark, quiet, slowly breathing. Never silent."""
    w = common.white(rng, n)
    w = np.sqrt(0.88) * w + np.sqrt(0.12) * common.white(rng, n, 1)
    low = _fft_shape(w, sr, lambda f: _band(f, 45, 520, 2, 2))
    hush = _fft_shape(common.white(rng, n), sr, lambda f: _band(f, 260, 2300, 2, 2))
    low /= low.std()
    hush /= hush.std()
    out = np.zeros((n, 2))
    for c in range(2):
        out[:, c] = low[:, c] * _cmod(rng, n, dur, 0.10, 0.22) + 0.42 * hush[:, c] * _cmod(rng, n, dur, 0.14, 0.30)
    return out / out.std()


def _swell(rng, n, sr, dur, sw):
    w = common.white(rng, n)
    w = np.sqrt(0.75) * w + np.sqrt(0.25) * common.white(rng, n, 1)
    lo = _fft_shape(w, sr, lambda f: _band(f, 70, 230, 2, 3))
    mid = _fft_shape(common.white(rng, n), sr, lambda f: _band(f, 160, 520, 2, 3))
    lo /= lo.std()
    mid /= mid.std()
    out = np.zeros((n, 2))
    for c in range(2):
        out[:, c] = lo[:, c] * sw * _cmod(rng, n, dur, 0.5, 0.18) + 0.8 * mid[:, c] * sw ** 1.6 * _cmod(rng, n, dur, 0.7, 0.2)
    return out


_WASH_FC = 110.0 * 2.0 ** (0.75 * np.arange(9))     # 110 Hz .. ~7 kHz


def _wash(rng, n, sr, dur, aw, bright, gl, gr):
    cut = 340.0 * (3300.0 / 340.0) ** bright
    base = common.white(rng, n)
    out = np.zeros((n, 2))
    for fc in _WASH_FC:
        band = _fft_shape(base, sr, lambda f, fc=fc: _band(f, fc / 1.34, fc * 1.34, 3, 3))
        band /= band.std()
        lp = 1.0 / np.sqrt(1.0 + (fc / cut) ** 4)
        a = (fc / 1000.0) ** -0.28
        for c in range(2):
            m = _cmod(rng, n, dur, 5.0 + 3.0 * rng.random(), 0.22) * _cmod(rng, n, dur, 0.9, 0.18)
            out[:, c] += band[:, c] * lp * a * m
    out *= aw[:, None]
    out[:, 0] *= gl
    out[:, 1] *= gr
    return out


def _foam(rng, n, sr, dur, fo, gl, gr, pn):
    """Foam: bubble pops that stay individually audible (a crackle, not a Gaussian noise floor) over a
    faint hiss. The pop rate is high enough to read as sizzle, but the amplitudes are heavy-tailed
    (lognormal, sigma ~0.85) and clustered in loose bursts, so grains stand out of the texture (the
    kurtosis of the 3-8 kHz band is ~5-10 at the foam peak instead of ~3.4 for plain hiss).
    Tilted like real foam: pops live at 1.5-4 kHz and only rare ones reach 6-8 kHz; the hiss is
    high-passed at 1.3 kHz and falls 6 dB/oct above FOAM_KNEE."""
    fo = np.minimum(fo, 1.25)
    hiss = _fft_shape(common.white(rng, n), sr, lambda f: _band(f, 1300, FOAM_KNEE, 3, 1))
    hiss /= hiss.std()
    out = np.zeros((n, 2))
    for c in range(2):
        out[:, c] = hiss[:, c] * _cmod(rng, n, dur, 45.0, 0.45) * fo * (gl, gr)[c] * HISS_GAIN

    # bubbles come in loose random bursts (random rate up to ~18 Hz), not as an even rain: this keeps the grains audible
    burst = np.maximum(1.0 + CLUSTER * common.circular_random(rng, n, 9.0, sr), 0.12)
    dens = fo ** 0.8 * burst
    tgrid = np.arange(n) / sr
    cdf = np.cumsum(dens)
    cdf /= cdf[-1]
    pops = [  # (peak rate /s, f lo, f hi, f skew, tau lo s, tau hi s, amp)
        (POP_RATE_A, 1700.0, 8000.0, 2.0, 0.00030, 0.00100, 0.55),
        (POP_RATE_B, 1200.0, 3600.0, 1.2, 0.00080, 0.00220, 0.60),
    ]
    mean_f = np.mean(dens)
    for rate, flo, fhi, skew, tlo, thi, pamp in pops:
        cnt = rng.poisson(rate * mean_f * dur)
        t0 = np.interp(rng.random(cnt), cdf, tgrid)
        starts = (t0 * sr).astype(np.int64) % n
        fv = np.minimum(fo[starts], 1.0)
        # as the foam drains the bubbles that remain are lower and quieter; the top octave is rare
        f0 = flo * (fhi / flo) ** (rng.random(cnt) ** skew) * (0.62 + 0.38 * fv)
        tau = np.exp(rng.uniform(np.log(tlo), np.log(thi), cnt)) * (1.0 + 0.4 * (1.0 - fv))
        amp = np.minimum(np.exp(POP_SIGMA * rng.standard_normal(cnt)), 5.5) * pamp * (0.4 + 0.6 * fv)
        pos = np.clip(pn[starts] * 1.0 + 0.5 * np.tanh(rng.standard_normal(cnt)), -0.95, 0.95)
        pl, pr = common.pan_gains(pos)
        glide = rng.uniform(0.10, 0.40, cnt)
        phi0 = rng.uniform(0, 2 * np.pi, cnt)
        dphi = rng.uniform(-1, 1, cnt) * np.pi * 0.6
        order = np.argsort(tau)
        B = 1500
        for i in range(0, cnt, B):
            ids = order[i:i + B]
            L = int(np.ceil(7.0 * tau[ids].max() * sr)) + 4
            t = (np.arange(L) / sr)[None, :]
            tg = 0.8 * tau[ids, None]
            # rising pitch (bubbles tighten as they form): phase = integral of f0*(1 + g*(1 - exp(-t/tg)))
            ph = 2 * np.pi * f0[ids, None] * ((1.0 + glide[ids, None]) * t
                                              - glide[ids, None] * tg * (1.0 - np.exp(-t / tg))) + phi0[ids, None]
            env = np.exp(-t / tau[ids, None]) * (1.0 - np.exp(-t / 6e-5)) * amp[ids, None]
            idx = ((starts[ids, None] + np.arange(L)[None, :]) % n).ravel()
            out[:, 0] += np.bincount(idx, (np.sin(ph) * env * pl[ids, None]).ravel(), minlength=n)
            out[:, 1] += np.bincount(idx, (np.sin(ph + dphi[ids, None]) * env * pr[ids, None]).ravel(), minlength=n)
    return out


# ------------------------------------------------------------------ entry point
def _layers(rng, sr):
    dur = META["duration_s"]
    period = dur - META["loop_xfade_s"]
    n = int(dur * sr)
    waves = _waves(rng, period)
    t, aw, br, sw, fo, pn = _tracks(waves, n, sr, period)
    surge = _surge(rng, n, sr, period)
    aw, sw = aw * surge, sw * surge                       # the water surges; the distant bed does not
    pn = pn + 0.10 * common.circular_random(rng, n, 0.10, sr)     # the shore image never sits dead centre
    ga, gb = common.pan_gains(pn)
    gl, gr = ga * np.sqrt(2.0), gb * np.sqrt(2.0)
    bright = np.clip(br, 0.0, 1.0) ** 0.75

    bed = _bed(rng, n, sr, dur)
    swell = _swell(rng, n, sr, dur, sw)
    wash = _wash(rng, n, sr, dur, aw, bright, gl, gr)
    foam = _foam(rng, n, sr, dur, fo, gl, gr, pn)

    # normalise each layer by its own level, then mix by explicit gains
    for layer in (wash, foam, swell):
        layer /= np.sqrt(np.mean(layer ** 2))
    return dict(bed=bed, swell=swell, wash=wash, foam=foam, waves=waves)


def generate(rng, sr):
    L = _layers(rng, sr)
    mix = BED_MIX * L["bed"] + 0.60 * L["swell"] + 1.00 * L["wash"] + FOAM_MIX * L["foam"]
    # soft top edge
    mix = _fft_shape(mix, sr, lambda f: 1.0 / np.sqrt(1.0 + (f / 9500.0) ** 4))
    return mix
