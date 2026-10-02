import numpy as np

from neurosync.app.presets import PresetRepository
from neurosync.app.session import Session, SessionState
from neurosync.domain.bands import BrainwaveBand
from neurosync.domain.limits import SAMPLE_RATE
from neurosync.domain.models import ChannelConfig, Preset


def preset():
    return Preset("t", BrainwaveBand.ALPHA, [ChannelConfig("binaural", "b", volume=1.0)])


def run(session, seconds, block=4800):
    peak = []
    for _ in range(int(seconds * SAMPLE_RATE / block)):
        peak.append(np.max(np.abs(session.render(block))))
    return peak


def test_builtin_presets_load_and_cover_bands():
    presets = PresetRepository().builtin()
    assert {"Alpha Focus", "Delta Sleep"} <= {p.name for p in presets}
    assert {p.band for p in presets} == set(BrainwaveBand)


def test_user_preset_roundtrip(tmp_path):
    repo = PresetRepository(tmp_path)
    p = Preset("Deep Work Rain", BrainwaveBand.ALPHA,
               [ChannelConfig("binaural", "b", base_hz=200, beat_hz=10.5),
                ChannelConfig("noise", "Pink", variant="pink", volume=0.3)])
    repo.save(p)
    loaded = repo.user()[0]
    assert loaded.to_dict() == p.to_dict()
    repo.delete(p.name)
    assert repo.user() == []


def test_idle_is_silent_and_play_makes_sound():
    s = Session(preset())
    assert max(run(s, 0.2)) == 0
    s.play()
    assert max(run(s, 0.5)) > 0.1


def test_stop_fades_over_at_least_3s_then_stops():
    s = Session(preset(), master_volume=0.8)
    s.play(); run(s, 0.5)
    done = []
    s.on_finished = lambda: done.append(1)
    s.stop(fade_s=0.1)                      # request shorter than minimum
    assert s.state is SessionState.FADING
    peaks = run(s, 2.9)
    assert s.state is SessionState.FADING and not done
    assert all(b <= a + 1e-3 for a, b in zip(peaks, peaks[1:]))  # monotonic decay
    run(s, 0.3)
    assert s.state is SessionState.STOPPED and done == [1]
    assert max(run(s, 0.2)) == 0


def test_timer_fades_before_end():
    s = Session(preset())
    s.set_timer(minutes=0.25, fade_minutes=0.1)   # 15 s total, 6 s fade
    s.play()
    run(s, 8)
    assert s.state is SessionState.PLAYING
    run(s, 2)
    assert s.state is SessionState.FADING
    run(s, 6)
    assert s.state is SessionState.STOPPED
