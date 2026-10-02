"""Render the main UI states to docs/screenshots (works headless: QT_QPA_PLATFORM=offscreen)."""
from __future__ import annotations

import sys
import tempfile
import time
from collections import namedtuple
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from neurosync.app.presets import PresetRepository
from neurosync.app.settings import Settings
from neurosync.domain.models import NOISE, ChannelConfig
from neurosync.infra.audio_output import SimulatedPlayer
from neurosync.ui.main_window import MainWindow
from neurosync.ui.theme import FONT_FAMILIES

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
Dev = namedtuple("Dev", "index name hostapi is_default")
DEVICES = [Dev(3, "Speakers (Realtek High Definition Audio)", "WASAPI", True),
           Dev(5, "Headphones (Schiit Modi+ DAC)", "WASAPI", False)]


def pump(seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents(); time.sleep(0.01)


def make(tmp: Path, **settings) -> MainWindow:
    s = Settings(disclaimer_accepted=True, **settings)
    def factory(render, device, exclusive):
        p = SimulatedPlayer(render); p.start(); return p
    w = MainWindow(repo=PresetRepository(tmp), settings=s, settings_dir=tmp,
                   player_factory=factory, devices=DEVICES)
    w.resize(1360, 840); w.show(); pump(0.3)
    return w


def shot(w: MainWindow, name: str) -> None:
    pump(0.2)
    w.grab().save(str(OUT / f"{name}.png"))
    print("saved", name)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    f = QFont(); f.setFamilies(FONT_FAMILIES); f.setPointSizeF(10); app.setFont(f)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())

    # 1. Quick focus: Alpha Focus playing
    w = make(tmp, master_volume=0.55)
    w.toggle_play(); pump(1.6)
    shot(w, "01-alpha-focus-playing")
    w.transport.stop(); w._release_player(); w.close(); w.deleteLater()

    # 2. First launch safety notice
    w = make(tmp); w.settings.disclaimer_accepted = False
    w._show_disclaimer(); pump(0.5)
    shot(w, "02-first-launch-disclaimer")
    w.deleteLater()

    # 3. Sleep: Delta + 45 min timer with 5 min fade
    w = make(tmp, last_preset="Delta Sleep", master_volume=0.35)
    w.topbar.popover.group.button(45).click()
    w.toggle_play(); pump(1.6)
    shot(w, "03-delta-sleep-timer")
    w.topbar.timer.showMenu = lambda: None
    w.transport.stop(); w._release_player(); w.deleteLater()

    # 4. Biohacker: custom generator, rain + pink, inline save
    w = make(tmp)
    w.new_session()
    w.mixer.strips[1].slider.setValue(105)          # beat 10.5 Hz
    w.transport.add_channel(ChannelConfig(NOISE, "Heavy Rain", variant="brown", volume=0.55))
    w.transport.add_channel(ChannelConfig(NOISE, "Pink Noise", variant="pink", volume=0.3, pan=-0.2))
    w.mixer.set_preset(w.transport.draft); w._update_band()
    w.toggle_play(); pump(1.2)
    w.mixer.begin_save("Deep Work Rain")
    shot(w, "04-custom-generator-save")
    w.save_preset("Deep Work Rain"); pump(0.4)
    shot(w, "05-saved-toast")
    w.transport.stop(); w._release_player(); w.deleteLater()

    # 6. Gamma + high contrast
    w = make(tmp, last_preset="Gamma Creativity", high_contrast=True)
    w.toggle_play(); pump(1.2)
    shot(w, "06-high-contrast")
    w.transport.stop(); w._release_player(); w.deleteLater()

    # 7. Theta + shortcuts overlay
    w = make(tmp, last_preset="Theta Meditation")
    w.help.open(); pump(0.4)
    shot(w, "07-shortcuts")
    w.deleteLater()


if __name__ == "__main__":
    main()
