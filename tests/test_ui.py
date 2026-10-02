import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from neurosync.app.presets import PresetRepository  # noqa: E402
from neurosync.app.session import SessionState  # noqa: E402
from neurosync.app.settings import Settings  # noqa: E402
from neurosync.app.transport import Transport  # noqa: E402
from neurosync.domain.bands import BrainwaveBand  # noqa: E402
from neurosync.domain.limits import MASTER_GAIN_MAX, SAMPLE_RATE  # noqa: E402
from neurosync.ui.main_window import MainWindow  # noqa: E402
from neurosync.ui.widgets import visual_pulse_hz  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class NullPlayer:
    def __init__(self, *a): pass
    def stop(self): pass


@pytest.fixture
def win(app, tmp_path):
    w = MainWindow(repo=PresetRepository(tmp_path), settings=Settings(disclaimer_accepted=True),
                   settings_dir=tmp_path, player_factory=lambda *a: NullPlayer(), devices=[])
    yield w
    w._release_player(); w.deleteLater()


def test_visual_pulse_never_flickers_fast():
    for hz in (0.5, 2, 10, 18, 40):
        assert visual_pulse_hz(hz) <= 1.25


def test_master_slider_maps_to_safe_range(win):
    win.topbar.master.setValue(100)
    assert win.transport.master == pytest.approx(MASTER_GAIN_MAX)


def test_beat_slider_recolours_accent_by_band(win):
    win.load_preset(win._find("Alpha Focus"))
    beat = win.mixer.strips[1]
    beat.slider.setValue(30)          # 3.0 Hz -> delta
    assert win._band is BrainwaveBand.DELTA
    assert win.transport.draft.channels[0].beat_hz == pytest.approx(3.0)
    assert win.transport.dirty


def test_save_preset_roundtrip_and_builtin_protected(win):
    win.new_session(); win.save_preset("My Test")
    assert "My Test" in [p.name for p in win.repo.user()] and not win.transport.dirty
    win.save_preset("Alpha Focus")      # refused
    assert "Alpha Focus" not in [p.name for p in win.repo.user()]


def test_disclaimer_blocks_ui_until_accepted(app, tmp_path):
    w = MainWindow(repo=PresetRepository(tmp_path), settings=Settings(), settings_dir=tmp_path,
                   player_factory=lambda *a: NullPlayer(), devices=[])
    app.processEvents()
    assert not w.topbar.isEnabled()
    w._disclaimer.ok.click()
    assert w.settings.disclaimer_accepted


def test_transport_pause_ramps_and_crossfade_is_silent_free_of_clicks(tmp_path):
    repo = PresetRepository(tmp_path); a, b = repo.builtin()[0], repo.builtin()[1]
    t = Transport(); t.load(a); t.play()
    t.render(4800)
    t.load(b)                              # crossfade while playing
    import numpy as np
    out = np.concatenate([t.render(512) for _ in range(40)])
    assert np.max(np.abs(np.diff(out[:, 0]))) < 0.3
    t.pause()
    for _ in range(20):
        t.render(512)
    assert t.session.state is SessionState.PAUSED
