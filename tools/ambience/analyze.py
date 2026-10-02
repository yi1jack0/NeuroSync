"""Quality gate + spectrogram for one generator.

    python tools/ambience/analyze.py <id> [--out DIR] [--no-png]

Renders the generator exactly as the build does (finalize -> ogg encode -> decode ->
loop-crossfade), measures it, prints a JSON report and writes DIR/<id>.png
(spectrogram / level envelope / PSD) that you can LOOK at. Exit code 0 = all gates pass.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402

from neurosync.engine.sources import make_loopable  # noqa: E402

BANDS = [("sub<60", 0, 60), ("low60-250", 60, 250), ("lowmid250-1k", 250, 1000),
         ("mid1-4k", 1000, 4000), ("high4-10k", 4000, 10000), ("air>10k", 10000, 24000)]


def load_gen(gen_id: str):
    return importlib.import_module("gen_" + gen_id.replace("-", "_"))


def render(mod, sr=common.SR):
    rng = np.random.default_rng(zlib.crc32(mod.META["id"].encode()))
    raw = mod.generate(rng, sr)
    return common.finalize(raw, sr=sr)


def window_rms(x, sr, win_s=0.5):
    w = int(win_s * sr)
    n = len(x) // w
    return np.sqrt((x[: n * w].reshape(n, w, -1) ** 2).mean(axis=(1, 2)))


def band_db(x, sr):
    f, p = signal.welch(x.mean(axis=1), sr, nperseg=8192)
    total = p.sum()
    return {name: round(float(10 * np.log10(max(p[(f >= lo) & (f < hi)].sum() / total, 1e-12))), 1)
            for name, lo, hi in BANDS}, f, p


def tonal_peak_db(f, p):
    """Largest narrow spectral peak above its neighbourhood (whines / ringing show up here)."""
    sm = signal.medfilt(10 * np.log10(p + 1e-18), 201)
    d = 10 * np.log10(p + 1e-18) - sm
    d[f < 40] = 0
    return float(d.max()), float(f[d.argmax()])


def analyze(mod, out_dir: Path | None, png=True):
    meta, sr = mod.META, common.SR
    x = render(mod, sr)
    n_expected = int(meta["duration_s"] * sr)
    fails: list[str] = []

    h1 = hashlib.md5(x.tobytes()).hexdigest()
    h2 = hashlib.md5(render(mod, sr).tobytes()).hexdigest()
    if h1 != h2:
        fails.append("not deterministic for a fixed seed")

    if x.shape != (n_expected, 2):
        fails.append(f"shape {x.shape} != ({n_expected}, 2)")
    if not np.isfinite(x).all():
        fails.append("NaN/Inf in output")

    raw = common.encode_ogg(x, sr)
    y, rate = common.decode_ogg(raw)
    if rate != sr:
        fails.append(f"decoded rate {rate}")

    peak = float(np.abs(y).max())
    rms = float(np.sqrt((y ** 2).mean()))
    dc = float(np.abs(y.mean(axis=0)).max())
    win = window_rms(y, sr)
    hi_ratio, lo_ratio = float(win.max() / win.mean()), float(win.min() / win.mean())
    corr = float(np.corrcoef(y[:, 0], y[:, 1])[0, 1])
    bands, f, p = band_db(y, sr)
    tonal_db, tonal_hz = tonal_peak_db(f, p)
    centroid = float((f * p).sum() / p.sum())

    loop = make_loopable(y, int(meta["loop_xfade_s"] * sr))
    seam_step = float(np.abs(loop[0] - loop[-1]).max())
    typical = float(np.percentile(np.abs(np.diff(loop, axis=0)), 99.9))
    h = int(0.5 * sr)
    before, after = loop[-h:], loop[:h]
    seam_level_db = float(20 * np.log10((np.sqrt((after ** 2).mean()) + 1e-9) /
                                        (np.sqrt((before ** 2).mean()) + 1e-9)))
    longest_quiet = float((window_rms(loop, sr, 0.25) < 0.25 * rms).sum() * 0.25)

    if peak > 0.95: fails.append(f"peak {peak:.3f} > 0.95")
    if not 0.12 <= rms <= 0.18: fails.append(f"rms {rms:.3f} outside 0.12..0.18")
    if dc > 0.003: fails.append(f"DC offset {dc:.4f}")
    if hi_ratio > 2.0: fails.append(f"loudest 0.5 s window is {hi_ratio:.2f}x mean (limit 2.0)")
    if lo_ratio < 0.4: fails.append(f"quietest 0.5 s window is {lo_ratio:.2f}x mean (limit 0.4): dropouts?")
    if meta.get("wide", True) and not -0.3 <= corr <= 0.6:
        fails.append(f"L/R correlation {corr:.2f} outside -0.3..0.6")
    if not meta.get("tonal_ok", False) and tonal_db > 18:
        fails.append(f"narrow tonal peak {tonal_db:.1f} dB at {tonal_hz:.0f} Hz (whine/ring)")
    if seam_step > max(3 * typical, 0.02): fails.append(f"loop seam step {seam_step:.3f} vs typical {typical:.3f}")
    if abs(seam_level_db) > 3: fails.append(f"level jumps {seam_level_db:+.1f} dB across loop seam")
    if longest_quiet > 1.0: fails.append(f"{longest_quiet:.2f} s of near-silence")
    if len(raw) > 900_000: fails.append(f"ogg is {len(raw) / 1e3:.0f} kB (limit 900 kB)")

    report = {
        "id": meta["id"], "pass": not fails, "failures": fails,
        "metrics": {"peak": round(peak, 3), "rms": round(rms, 4), "crest_db": round(20 * np.log10(peak / rms), 1),
                    "dc": round(dc, 5), "short_term_max_over_mean": round(hi_ratio, 2),
                    "short_term_min_over_mean": round(lo_ratio, 2), "lr_corr": round(corr, 2),
                    "spectral_centroid_hz": round(centroid), "band_energy_db": bands,
                    "tonal_peak_db": round(tonal_db, 1), "tonal_peak_hz": round(tonal_hz),
                    "seam_step": round(seam_step, 4), "seam_typical_step": round(typical, 4),
                    "seam_level_db": round(seam_level_db, 2), "ogg_kB": round(len(raw) / 1e3),
                    "duration_s": round(len(y) / sr, 2)},
    }
    if png and out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{meta['id']}.png"
        plot(y, sr, meta, path)
        report["png"] = str(path)
    return report


def plot(y, sr, meta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [3, 1.2, 1.6]})
    mono = y.mean(axis=1)
    ax[0].specgram(mono, NFFT=2048, Fs=sr, noverlap=1536, cmap="magma", vmin=-130, vmax=-30)
    ax[0].set_yscale("symlog", linthresh=500); ax[0].set_ylim(0, 20000)
    ax[0].set_title(f"{meta['name']} - spectrogram (log freq, dB)  |  duration {len(y) / sr:.1f}s")
    ax[0].set_ylabel("Hz")
    w = int(0.1 * sr); n = len(mono) // w
    env = 20 * np.log10(np.sqrt((mono[: n * w].reshape(n, w) ** 2).mean(axis=1)) + 1e-6)
    ax[1].plot(np.arange(n) * 0.1, env, lw=1); ax[1].set_ylabel("dBFS (0.1 s RMS)")
    ax[1].set_xlim(0, len(y) / sr); ax[1].grid(alpha=.3)
    f, p = signal.welch(mono, sr, nperseg=8192)
    ax[2].semilogx(f[1:], 10 * np.log10(p[1:] + 1e-18), lw=1)
    ref = 10 * np.log10(p[np.searchsorted(f, 1000)] + 1e-18) - 10 * np.log10(f[1:] / 1000)
    ax[2].semilogx(f[1:], ref, "--", lw=.8, label="-3 dB/oct (pink) reference")
    ax[2].set_xlim(20, 24000); ax[2].set_ylabel("PSD dB"); ax[2].set_xlabel("Hz")
    ax[2].grid(alpha=.3, which="both"); ax[2].legend(loc="upper right")
    fig.tight_layout(); fig.savefig(path, dpi=80); plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("id"); ap.add_argument("--out", default="/tmp/ambience-analysis")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()
    rep = analyze(load_gen(a.id), Path(a.out), png=not a.no_png)
    print(json.dumps(rep, indent=1, default=float))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
