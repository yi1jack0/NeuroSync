import numpy as np
import pytest

from neurosync.domain.limits import MASTER_GAIN_MAX, MIN_FADE_OUT_S, SAMPLE_RATE
from neurosync.domain.models import ChannelConfig
from neurosync.engine.fade import LogFade
from neurosync.engine.mixer import MixerChannel, MixerEngine
from neurosync.engine.sources import OscillatorSource, SampleSource, make_noise_buffer


def dominant_hz(x):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1 / SAMPLE_RATE)[np.argmax(spec)]


def test_binaural_channels_differ_by_beat():
    out = OscillatorSource(200, 10).read(SAMPLE_RATE)
    assert dominant_hz(out[:, 0]) == pytest.approx(200, abs=1)
    assert dominant_hz(out[:, 1]) == pytest.approx(210, abs=1)


def test_oscillator_is_block_size_independent_and_continuous():
    a, b = OscillatorSource(200, 10), OscillatorSource(200, 10)
    whole = a.read(4800)
    parts = np.concatenate([b.read(1000), b.read(1800), b.read(2000)])
    assert np.allclose(whole, parts, atol=1e-4)


def test_frequency_change_has_no_click():
    osc = OscillatorSource(200, 10)
    osc.read(1000)
    osc.set_frequencies(base_hz=900)
    out = osc.read(2000)
    assert np.max(np.abs(np.diff(out[:, 0]))) < 0.2  # no discontinuity


def test_frequency_limits_clamped():
    osc = OscillatorSource(5000, 99)
    assert osc._base == 1000 and osc._beat == 40
    cfg = ChannelConfig("binaural", "x", base_hz=1, beat_hz=0)
    assert cfg.base_hz == 50 and cfg.beat_hz == 0.1


def test_master_gain_never_exceeds_cap_even_when_summed():
    mixer = MixerEngine()
    for _ in range(6):
        mixer.channels.append(MixerChannel("o", OscillatorSource(), volume=1.0, is_binaural=True))
    mixer.master_volume = 5.0
    assert mixer.master_volume == MASTER_GAIN_MAX
    mixer.render(2000)
    assert np.max(np.abs(mixer.render(4800))) <= MASTER_GAIN_MAX + 1e-6


def test_mute_and_pan():
    src = SampleSource(np.ones((100, 2), dtype=np.float32))
    ch = MixerChannel("n", src, volume=1.0, pan=1.0)
    ch.render(10); out = ch.render(10)
    assert np.allclose(out[:, 0], 0) and np.allclose(out[:, 1], 1)
    ch.is_muted = True
    ch.render(10)
    assert np.allclose(ch.render(10), 0)


def test_noise_loops_seamlessly_and_pink_tilts():
    buf = make_noise_buffer("pink", seconds=2, seed=1)
    assert np.max(np.abs(buf)) <= 0.7 + 1e-6
    spec = np.abs(np.fft.rfft(buf[:, 0])) ** 2
    f = np.fft.rfftfreq(len(buf), 1 / SAMPLE_RATE)
    lo = spec[(f > 100) & (f < 200)].mean()
    hi = spec[(f > 1600) & (f < 3200)].mean()
    assert lo > hi * 5  # power falls ~1/f


def test_fade_is_log_min_3s_and_reaches_zero():
    fade = LogFade(0.5)
    assert fade.total == int(MIN_FADE_OUT_S * SAMPLE_RATE)
    g = fade.gains(fade.total)
    assert g[0] == pytest.approx(1.0) and np.all(np.diff(g) <= 1e-9)
    assert g[-1] == pytest.approx(0.0, abs=1e-6)
    assert g[fade.total // 2] == pytest.approx(10 ** (-30 / 20), rel=0.05)  # -30 dB at midpoint
    assert fade.done
