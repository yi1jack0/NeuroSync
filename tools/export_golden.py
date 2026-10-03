"""Export reference values from the desktop (Python) engine for the web port's tests.

    python tools/export_golden.py      -> web/src/domain/golden.json
The web unit tests (web/src/domain/golden.test.ts) must reproduce every number.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from neurosync.app.presets import PresetRepository
from neurosync.domain.bands import BrainwaveBand
from neurosync.domain.limits import (BASE_FREQ_MAX_HZ, BASE_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ,
                                     BEAT_FREQ_MIN_HZ, FADE_FLOOR_DB, MASTER_GAIN_MAX,
                                     MIN_FADE_OUT_S)
from neurosync.domain.models import ChannelConfig
from neurosync.engine.fade import LogFade
from neurosync.engine.sources import make_loopable

OUT = Path(__file__).resolve().parents[1] / "web" / "src" / "domain" / "golden.json"


def main() -> None:
    limits = dict(base_min=BASE_FREQ_MIN_HZ, base_max=BASE_FREQ_MAX_HZ, beat_min=BEAT_FREQ_MIN_HZ,
                  beat_max=BEAT_FREQ_MAX_HZ, master_max=MASTER_GAIN_MAX, min_fade_s=MIN_FADE_OUT_S,
                  fade_floor_db=FADE_FLOOR_DB)

    clamp_cases = []
    for base, beat, vol, pan in [(5, 0, 2, -3), (2000, 99, -1, 3), (200, 10.5, 0.4, 0.2), (50, 0.1, 1, -1)]:
        c = ChannelConfig("binaural", "x", base_hz=base, beat_hz=beat, volume=vol, pan=pan)
        clamp_cases.append({"in": [base, beat, vol, pan], "out": [c.base_hz, c.beat_hz, c.volume, c.pan]})

    bands = [{"hz": hz, "band": BrainwaveBand.for_frequency(hz).name}
             for hz in (0.1, 0.5, 3.99, 4, 7.9, 8, 10.5, 13.99, 14, 29.9, 30, 40, 120)]

    fade = LogFade(3.0, sample_rate=1000)            # 3000 samples
    g = fade.gains(fade.total)
    fade_points = [{"t": i / fade.total, "gain": float(g[i])} for i in (0, 300, 750, 1500, 2250, 2900, 2970, 2999)]

    t = np.arange(64)
    data = np.stack([np.sin(t * 0.3), np.linspace(-1, 1, 64)], axis=1).astype(np.float32)
    loop = make_loopable(data, 16)

    presets = [p.to_dict() for p in PresetRepository(Path("/nonexistent")).builtin()]

    golden = {
        "limits": limits,
        "clamp": clamp_cases,
        "bands": bands,
        "fade": {"duration_s": 3.0, "points": fade_points},
        "loopable": {"xfade": 16, "input": data.T.round(7).tolist(), "output": loop.T.round(7).tolist()},
        "master_slider": [{"slider": v, "gain": v / 100 * MASTER_GAIN_MAX} for v in (0, 25, 50, 100)],
        "presets": presets,
    }
    OUT.write_text(json.dumps(golden, indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
