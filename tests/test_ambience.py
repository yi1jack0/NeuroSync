import numpy as np
import pytest

from neurosync.app.builder import AudioGraphBuilder
from neurosync.assets import ASSET_PREFIX, catalog, get_sound, read_asset_bytes
from neurosync.domain.bands import BrainwaveBand
from neurosync.domain.limits import SAMPLE_RATE
from neurosync.domain.models import SAMPLE, ChannelConfig, Preset
from neurosync.engine.sources import (SampleSource, decode_bytes, make_loopable, to_int16)

SHIPPED = {"river-gentle", "river-deep", "sea-calm"}


# ---------------------------------------------------------------- loader maths
def test_make_loopable_is_continuous_and_keeps_level():
    rng = np.random.default_rng(0)
    data = (rng.standard_normal((48000 * 6, 2)) * 0.1).astype(np.float32)
    xf = 48000
    loop = make_loopable(data, xf)
    assert len(loop) == len(data) - xf
    # wrap seam = two consecutive source frames -> same step size as anywhere else
    assert np.abs(loop[0] - loop[-1]).max() <= np.abs(np.diff(data, axis=0)).max()
    # equal-power blend of uncorrelated noise keeps RMS
    assert loop[:xf].std() == pytest.approx(data.std(), rel=0.08)


def test_sample_source_int16_matches_float_and_wraps():
    rng = np.random.default_rng(1)
    f = (rng.uniform(-0.5, 0.5, (1000, 2))).astype(np.float32)
    a, b = SampleSource(to_int16(f)), SampleSource(f)
    for _ in range(7):  # 7 * 300 frames wraps the 1000-frame buffer twice
        assert np.allclose(a.read(300), b.read(300), atol=1e-4)
    assert a._buf.nbytes == 1000 * 2 * 2          # int16 = half the memory of float32


# ---------------------------------------------------------------- shipped catalog
def test_catalog_contains_requested_sounds():
    assert SHIPPED <= {s.id for s in catalog()}
    for sid in SHIPPED:
        assert get_sound(sid).category == "Water"


@pytest.mark.parametrize("sound", catalog(), ids=lambda s: s.id)
def test_asset_file_quality(sound):
    data, rate = decode_bytes(read_asset_bytes(sound.file))
    assert rate == SAMPLE_RATE and data.shape[1] == 2
    assert len(data) / rate == pytest.approx(sound.duration_s, abs=0.05)
    assert np.isfinite(data).all()
    assert np.abs(data).max() <= 0.95                          # headroom under the master cap
    assert 0.11 <= float(np.sqrt((data ** 2).mean())) <= 0.19   # consistent loudness across beds
    assert abs(float(data.mean())) < 0.003                      # no DC
    assert len(read_asset_bytes(sound.file)) < 900_000
    assert 0 < sound.default_volume <= 1 and sound.description


@pytest.mark.parametrize("sound", catalog(), ids=lambda s: s.id)
def test_asset_loops_without_click(sound):
    src = SampleSource.from_asset(sound.id)
    n = len(src._buf)
    assert n == pytest.approx((sound.duration_s - sound.loop_xfade_s) * SAMPLE_RATE, abs=2)
    out = np.concatenate([src.read(512) for _ in range(int(2.2 * n / 512))])  # > 2 wraps
    steps = np.abs(np.diff(out, axis=0)).max(axis=1)
    seam = n  # first wrap
    assert steps[seam - 2:seam + 2].max() <= 3 * np.percentile(steps, 99.9) + 1e-3


def test_assets_share_one_decoded_buffer():
    a, b = SampleSource.from_asset("sea-calm"), SampleSource.from_asset("sea-calm")
    assert a._buf is b._buf                                    # cached: no duplicate RAM


def test_total_bundle_size_and_memory_budget():
    total = sum(len(read_asset_bytes(s.file)) for s in catalog())
    assert total < 6_000_000
    ram = sum(len(SampleSource.from_asset(s.id)._buf) * 4 for s in catalog())  # int16 stereo
    assert ram < 30e6


def test_preset_with_asset_channel_builds_and_renders():
    p = Preset("t", BrainwaveBand.THETA, [
        ChannelConfig(SAMPLE, "Sea", path=ASSET_PREFIX + "sea-calm", volume=1.0)])
    mixer = AudioGraphBuilder().build(p, master_volume=0.85)
    mixer.render(2000)
    out = mixer.render(SAMPLE_RATE)
    assert 0.02 < np.abs(out).max() <= 0.85 + 1e-6


def test_unknown_asset_raises():
    with pytest.raises(ValueError):
        get_sound("nope")
