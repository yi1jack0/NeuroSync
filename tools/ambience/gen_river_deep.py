"""River (deep): a wide, deep river with a strong, smooth, steady current.

A full rounded 'whoosh' of moving water: dark, with lots of body at 100-800 Hz, soft dense
texture, a gentle turbulent rumble, only a sprinkling of low, soft, large-bubble 'gloops',
a thin quiet high shimmer, and slow broad swells / eddies that drift differently on L and R.

Construction (everything is periodic over the file so the loop crossfade is seamless):
  * a bank of band-limited pink-ish noise layers made directly in the FFT domain (zero-phase,
    circular, no filter warm-up), each modulated independently per channel by slow circular
    curves (level swell + spectral tilt + per-band wander) and a soft fast 'burble', plus one
    shallow 1/f-like (0.4-8 Hz) co-modulator, mostly common to both ears and slightly time-
    shifted per band, so the body of the sound is lively water rather than stationary noise
    without any audible surge rate.  The slow swell / tilt / emphasis curves carry an
    opposed-pan part (L up while R down), so the current drifts across the stereo field
    while the mono level stays steady;
  * a soft granular layer of tiny low-frequency bubble chirps (dense, quiet) for body texture;
  * a sparse set of large soft bubbles (rising-chirp damped sines, 150-900 Hz);
  * a quiet, crackly 3-8 kHz shimmer.
"""
from __future__ import annotations

import numpy as np

import common

META = dict(
    id="river-deep",
    name="Deep River",
    category="Water",
    description="A broad, deep river with a steady, rounded rushing current and slow, drifting eddies.",
    loop_xfade_s=3.0,
    duration_s=30,
    default_volume=0.5,
    order=2,
    wide=True,
    tonal_ok=False,
)

# (centre Hz, octave-power weight dB, shared L/R fraction, burble depth, burble max Hz)
BANDS = [
    (65,    -9.0, 0.45, 0.00, 0),
    (100,   -4.0, 0.40, 0.04, 3),
    (150,   -0.5, 0.35, 0.08, 5),
    (230,    0.5, 0.30, 0.10, 6),
    (350,    1.0, 0.25, 0.12, 8),
    (520,    0.5, 0.22, 0.15, 10),
    (780,   -0.5, 0.20, 0.18, 12),
    (1150,   1.0, 0.15, 0.22, 14),
    (1700,  -0.2, 0.12, 0.26, 18),
    (2500,  -2.5, 0.10, 0.32, 22),
    (3700,  -7.0, 0.06, 0.42, 30),
    (5500, -13.0, 0.04, 0.50, 40),
    (8000, -22.0, 0.03, 0.55, 45),
    (11500, -29.0, 0.02, 0.50, 45),
]
SIGMA_OCT = 0.46     # half-width of each band's gaussian (in octaves)

# Shared fast co-modulation of the bed below ~3 kHz (water is bubble-driven, so its bands
# swell and ebb a little together): log-gain depth (nepers per unit-std curve) and the curve's
# rate range in Hz.  The curve is 1/f-like (EXP 0.9) and reaches down to 0.4 Hz with no empty
# band, so it reads as turbulence rather than as a modulator with a rate (no 2-3 Hz 'chuff').
# Kept shallow: a deep, smooth current must not surge.
SHARED_DEPTH = 0.25
SHARED_F_LO, SHARED_F_HI, SHARED_EXP = 0.4, 8.0, 0.9
# fraction of the curve that is common to L and R.  Mostly common, so the quick surges hit
# both ears together and the image does not ping-pong; the L/R difference lives in the slow
# swell / tilt / spectral-emphasis terms below instead (they are what moves across the field).
SHARED_COMMON = 0.8
# each band sees the shared curve slightly shifted in time (+-SHARED_LAG_S, circular) so the
# bursts are not simultaneous across the whole 200-2500 Hz body
SHARED_LAG_S = 0.07
# how much of SHARED_DEPTH each band takes, by centre Hz (low rumble stays smooth, no thumping)
SHARED_PROFILE = ((65, 0.25), (100, 0.4), (150, 0.65), (230, 0.9), (350, 1.0), (780, 1.0),
                  (1150, 0.9), (1700, 0.65), (2500, 0.45))

# Slow L/R drift of the bed (a few tenths of Hz), as weights of (common, opposed-pan,
# independent-per-ear) unit curves, and the level-swell depth in dB per unit curve.  The 'pan'
# curve moves the two ears in opposite directions (L up while R down), so the current drifts
# across the stereo field while the mono level stays steady; the independent part keeps the
# two ears from ever being a mirror image.
SWELL_W = (0.45, 0.80, 0.60)
TILT_W = (0.50, 0.80, 0.55)
SWIRL_W = (0.50, 0.80, 0.55)
SWELL_DB = 1.3


# ------------------------------------------------------------------ helpers
def _smooth(rng, n, sr, f_hi, channels=2, f_lo=0.0, exponent=0.0):
    """Unit-std periodic smooth random curves, band-limited to [f_lo, f_hi] Hz. (n, channels).
    `exponent` tilts the curve's spectrum (amplitude ~ f^-exponent; 0.5 = 1/f 'flicker')."""
    k_hi = max(2, int(round(f_hi * n / sr)))
    k_lo = max(1, int(round(f_lo * n / sr)))
    out = np.empty((n, channels))
    for c in range(channels):
        spec = np.zeros(n // 2 + 1, dtype=complex)
        ks = np.arange(k_lo, k_hi + 1)
        taper = 0.5 * (1 + np.cos(np.pi * np.clip((ks - 0.6 * k_hi) / (0.4 * k_hi + 1e-9), 0, 1)))
        spec[k_lo:k_hi + 1] = ((rng.standard_normal(len(ks)) + 1j * rng.standard_normal(len(ks)))
                               * taper * ks ** -exponent)
        y = np.fft.irfft(spec, n)
        out[:, c] = y / (y.std() or 1.0)
    return out


def _lr_curves(rng, n, sr, f_hi, w):
    """Slow periodic (n, 2) L/R curves: common*c + (+-)pan*p + independent*(l, r)."""
    c = _smooth(rng, n, sr, f_hi, 4)         # [L, R, common, pan]
    return np.stack([w[0] * c[:, 2] + w[1] * c[:, 3] + w[2] * c[:, 0],
                     w[0] * c[:, 2] - w[1] * c[:, 3] + w[2] * c[:, 1]], axis=1)


def _band_noise(rng, n, sr, fc, channels=2, sigma=SIGMA_OCT, spec_exp=0.5):
    """Unit-std circular band-limited noise (log-gaussian band, pink-ish inside)."""
    f = np.fft.rfftfreq(n, 1.0 / sr)
    f[0] = f[1]
    resp = np.exp(-0.5 * (np.log2(f / fc) / sigma) ** 2) * f ** -spec_exp
    out = np.empty((n, channels))
    for c in range(channels):
        spec = (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))) * resp
        spec[0] = 0
        y = np.fft.irfft(spec, n)
        out[:, c] = y / (y.std() or 1.0)
    return out


def _db(x):
    return 10.0 ** (x / 20.0)


# ------------------------------------------------------------------ layers
def _bed(rng, n, sr):
    """Noise-band bank with independent slow modulation per band & channel."""
    # level swell + spectral tilt: current drifts across the stereo field
    sw = _lr_curves(rng, n, sr, 0.30, SWELL_W)
    tl = _lr_curves(rng, n, sr, 0.22, TILT_W)
    # a broad, soft spectral emphasis that drifts up and down (octaves rel. 600 Hz), differently
    # on L and R: the 'body of the current' moving past the listener
    fm = -0.35 + 0.75 * _lr_curves(rng, n, sr, 0.20, SWIRL_W)
    # one shallow 1/f-like co-modulator for the bands below ~3 kHz: they swell and ebb a little
    # together (so the body is not just stationary noise), instead of the independent per-band
    # burble that averages out across the overlapping bands
    sf = _smooth(rng, n, sr, SHARED_F_HI, 3, f_lo=SHARED_F_LO, exponent=SHARED_EXP)
    sf = np.stack([SHARED_COMMON ** 0.5 * sf[:, 2] + (1 - SHARED_COMMON) ** 0.5 * sf[:, 0],
                   SHARED_COMMON ** 0.5 * sf[:, 2] + (1 - SHARED_COMMON) ** 0.5 * sf[:, 1]], axis=1)
    prof_f, prof_w = zip(*SHARED_PROFILE)
    out = np.zeros((n, 2))
    for fc, wdb, share, burble, bmax in BANDS:
        common_n = _band_noise(rng, n, sr, fc, 1)
        indep = _band_noise(rng, n, sr, fc, 2)
        x = np.sqrt(share) * common_n + np.sqrt(1 - share) * indep
        wander = _smooth(rng, n, sr, 0.45, 2)
        oct_ = np.log2(fc / 600.0)
        swirl = 2.6 * np.exp(-0.5 * ((oct_ - fm) / 0.85) ** 2)       # drifting broad emphasis
        gdb = SWELL_DB * sw + 0.7 * oct_ * tl + 0.9 * wander + swirl
        g = _db(gdb)
        if burble > 0:
            fast = _smooth(rng, n, sr, bmax, 2, f_lo=0.6)
            g = g * np.exp(burble * fast - 0.5 * burble ** 2)
        if fc < 3000:
            d = SHARED_DEPTH * float(np.interp(np.log2(fc), np.log2(prof_f), prof_w))
            lag = int(rng.uniform(-1.0, 1.0) * SHARED_LAG_S * sr)
            g = g * np.exp(d * np.roll(sf, lag, axis=0) - 0.5 * d ** 2)
        out += _db(wdb) * g * x
    return out


def _texture(rng, n, sr):
    """Dense, very soft layer of tiny rising-chirp bubbles -> 'babbling' body texture.

    Vectorised: for each frequency class a random impulse train is circularly convolved
    (FFT multiply) with one soft chirped damped-sine kernel."""
    dur = n / sr
    out = np.zeros((n, 2))
    classes = np.geomspace(220, 1800, 12)
    swell = _smooth(rng, n, sr, 0.25, 1)[:, 0]
    for fc in classes:
        tau = 11.0 / (np.pi * fc)                           # Q ~ 11
        L = int(min(0.08, 7 * tau) * sr)
        t = np.arange(L) / sr
        phase = 2 * np.pi * fc * (t + 0.25 * t * t / tau * np.exp(-t / (2 * tau)))
        ker = np.sin(phase) * (1 - np.exp(-t / (0.35 * tau + 4e-4))) * np.exp(-t / tau)
        kf = np.fft.rfft(ker, n)
        for ch in range(2):
            m = rng.poisson(110.0 * dur)                    # events per class and channel
            pos = rng.integers(0, n, m)
            keep = rng.random(m) < np.exp(0.6 * swell[pos]) / 1.8
            pos = pos[keep]
            amp = np.exp(0.8 * rng.standard_normal(len(pos))) * rng.choice([-1.0, 1.0], len(pos))
            imp = np.bincount(pos, weights=amp, minlength=n)
            y = np.fft.irfft(np.fft.rfft(imp) * kf, n)
            out[:, ch] += y / (y.std() or 1.0) * _db(-4.0 - 6.0 * np.log2(fc / 220) / 3.0)
    return out


def _gloops(rng, n, sr):
    """Sparse, large, soft bubbles: damped sines with a rising chirp, 150-900 Hz.

    Inter-arrival times are gamma-distributed (loosely spread, never rhythmic) and a
    bubble sometimes spawns a smaller companion a moment later; placement wraps around."""
    dur = n / sr
    out = np.zeros((n, 2))
    times = []
    t = rng.uniform(0, 1.2)
    while t < dur:
        times.append(t)
        if rng.random() < 0.28:
            times.append(t + rng.uniform(0.07, 0.30))
        t += rng.gamma(2.0, 0.62)
    for tt in times:
        s = int(tt * sr) % n
        f0 = 150.0 * (900.0 / 150.0) ** (rng.random() ** 1.3)
        tau = rng.uniform(0.035, 0.085) * (300.0 / f0) ** 0.35
        c = rng.uniform(0.35, 0.9)                         # relative chirp rise over the decay
        L = int(min(0.45, 8 * tau) * sr)
        t_ = np.arange(L) / sr
        phase = 2 * np.pi * f0 * (t_ + c * t_ * t_ / (2 * tau) * np.exp(-t_ / (2.5 * tau)))
        env = (1 - np.exp(-t_ / 0.006)) * np.exp(-t_ / tau)
        g = np.sin(phase) * env
        g += 0.25 * np.sin(2 * phase + rng.uniform(0, 6.28)) * env ** 2   # slight roundness
        amp = 2.8 * 10 ** (-rng.uniform(0, 8) / 20)
        gl, gr = common.pan_gains(rng.uniform(-0.85, 0.85))
        common.add_at_circular(out, s, g * amp, gl, gr)
    return out


def _shimmer(rng, n, sr):
    """Quiet, fine high-frequency crackle in 3-8 kHz (not a steady hiss)."""
    out = np.zeros((n, 2))
    for fc, w in ((3600, -9.0), (5200, -9.5), (7200, -11.0)):
        x = _band_noise(rng, n, sr, fc, 2, sigma=0.5, spec_exp=0.0)
        fast = _smooth(rng, n, sr, 60, 2, f_lo=3)
        slow = _smooth(rng, n, sr, 0.3, 2)
        out += _db(w) * x * np.exp(0.85 * fast - 0.36) * _db(1.5 * slow)
    return out


# ------------------------------------------------------------------ main
def generate(rng, sr):
    n = int(META["duration_s"] * sr)
    bed = _bed(rng, n, sr)
    bed /= np.sqrt(np.mean(bed ** 2))
    tex = _texture(rng, n, sr)
    tex /= np.sqrt(np.mean(tex ** 2))
    glo = _gloops(rng, n, sr)
    shim = _shimmer(rng, n, sr)
    shim /= np.sqrt(np.mean(shim ** 2))
    mix = bed + 0.25 * tex + 1.0 * glo + 0.10 * shim
    return mix
