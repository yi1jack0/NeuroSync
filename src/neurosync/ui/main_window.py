"""Main window: assembles the regions and acts as the UI controller over Transport."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QMainWindow, QMenu,
                               QSystemTrayIcon, QVBoxLayout)

from ..app.presets import PresetRepository
from ..assets import ASSET_PREFIX, get_sound
from ..app.session import SessionState
from ..app.settings import Settings
from ..app.transport import Transport
from ..domain.bands import BrainwaveBand
from ..domain.limits import MASTER_GAIN_MAX
from ..domain.models import BINAURAL, NOISE, SAMPLE, ChannelConfig, Preset
from .icons import icon
from .overlays import DisclaimerOverlay, ShortcutsOverlay
from .panels import (CenterStage, MixerPanel, PresetLibrary, TopBar, binaural_of)
from .theme import DARK, HIGH_CONTRAST, band_color, strip_qss, stylesheet
from .widgets import AuroraBackground, Toast

NOISE_NAMES = {"pink": "Pink Noise", "brown": "Brown Noise", "white": "White Noise"}


def _fmt_time(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class MainWindow(QMainWindow):
    def __init__(self, repo: PresetRepository | None = None, settings: Settings | None = None,
                 settings_dir: Path | None = None,
                 player_factory: Callable | None = None,
                 devices: list | None = None) -> None:
        super().__init__()
        self.repo = repo or PresetRepository()
        self.settings_dir = settings_dir
        self.settings = settings or Settings.load(settings_dir)
        self.transport = Transport()
        self.transport.set_master(self.settings.master_volume)
        self._player_factory = player_factory or self._default_player
        self._player = None
        self._quitting = False
        self._timer_armed = False
        self._band: BrainwaveBand | None = None
        self._premute_volume = 0.0

        self.setWindowTitle("NeuroSync Studio")
        self.setMinimumSize(1160, 740)
        self.resize(1320, 820)

        # ---- layout --------------------------------------------------------
        self.root = AuroraBackground()
        self.setCentralWidget(self.root)
        outer = QVBoxLayout(self.root); outer.setContentsMargins(16, 16, 16, 16); outer.setSpacing(14)
        self.topbar = TopBar(self.settings.fade_minutes)
        outer.addWidget(self.topbar)
        body = QHBoxLayout(); body.setSpacing(14)
        self.library = PresetLibrary()
        self.stage = CenterStage()
        self.mixer = MixerPanel()
        body.addWidget(self.library); body.addWidget(self.stage, 1); body.addWidget(self.mixer)
        outer.addLayout(body, 1)
        self.toast = Toast(self.root)
        self.help = ShortcutsOverlay(self.root)
        self.setTabOrder(self.library.search, self.library.list)

        # ---- wiring ----------------------------------------------------------
        tb = self.topbar
        tb.play.clicked.connect(self.toggle_play)
        tb.stop.clicked.connect(self.stop)
        tb.master.setValue(TopBar.gain_to_slider(self.settings.master_volume))
        tb.master_pct.setText(f"{tb.master.value()}%")
        tb.master.valueChanged.connect(self._master_changed)
        tb.mute.toggled.connect(self._mute_master)
        tb.popover.changed.connect(self._timer_changed)
        tb.to_tray.clicked.connect(self.to_tray)
        tb.more.setMenu(self._build_menu())
        self.library.presetChosen.connect(self.load_preset)
        self.library.newRequested.connect(self.new_session)
        self.library.contextRequested.connect(self._preset_context)
        self.mixer.channelChanged.connect(self._channel_changed)
        self.mixer.addRequested.connect(self._add_channel)
        self.mixer.removeRequested.connect(self._remove_channel)
        self.mixer.saveRequested.connect(self.save_preset)

        self._devices = devices if devices is not None else self._list_devices()
        self._fill_devices()
        tb.device.currentIndexChanged.connect(self._device_changed)

        self._shortcuts()
        self.tray = self._build_tray()

        self._poll = QTimer(self); self._poll.timeout.connect(self._tick); self._poll.start(200)

        # ---- initial state -------------------------------------------------
        self.refresh_library()
        start = self._find(self.settings.last_preset) or self.repo.builtin()[0]
        self.load_preset(start)
        self.apply_theme()
        self._tick()
        self.topbar.play.setFocus()
        if not self.settings.disclaimer_accepted:
            QTimer.singleShot(0, self._show_disclaimer)

    # =====================================================================
    # theme
    # =====================================================================
    @property
    def palette_(self):
        return HIGH_CONTRAST if self.settings.high_contrast else DARK

    @property
    def accent(self) -> QColor:
        return band_color(self._band or BrainwaveBand.ALPHA)

    def apply_theme(self) -> None:
        pal, acc = self.palette_, self.accent
        self.setStyleSheet(stylesheet(pal, acc) + strip_qss(pal, acc))
        self.root.set_theme(pal, acc)
        self.topbar.set_theme(pal, acc)
        self.library.set_theme(pal, acc)
        self.mixer.set_theme(pal, acc)
        self.stage.orb.set_color(acc if pal.glass else QColor("#FFFFFF"))
        self.stage.orb.set_glass(pal.glass)
        self.stage.orb.reduce_motion = self.settings.reduce_motion
        self.topbar.set_playing(self.transport.is_playing)
        if self.tray:
            self.tray.setIcon(icon("orb", acc, 32))

    def _update_band(self) -> None:
        """Accent follows the *current* beat, so dragging across bands recolours the app."""
        b = binaural_of(self.transport.draft)
        band = BrainwaveBand.for_frequency(b.beat_hz) if b else self.transport.draft.band
        if band != self._band:
            self._band = band
            self.apply_theme()
        self.stage.show_preset(self.transport.draft, band, self.transport.dirty)
        self.mixer.set_dirty(self.transport.dirty)

    # =====================================================================
    # presets
    # =====================================================================
    def refresh_library(self) -> None:
        current = self.transport.draft.name if self.transport.draft else self.settings.last_preset
        self.library.populate(self.repo.builtin(), self.repo.user(), current)

    def _find(self, name: str) -> Preset | None:
        return next((p for p in self.repo.all() if p.name == name), None)

    def load_preset(self, preset: Preset) -> None:
        self.transport.load(preset)
        self.settings.last_preset = preset.name
        self.mixer.set_preset(self.transport.draft)
        self.library.set_current(preset.name)
        self.mixer.end_save()
        self._update_band()
        self._save_settings()

    def new_session(self) -> None:
        blank = Preset("Untitled session", BrainwaveBand.ALPHA,
                       [ChannelConfig(BINAURAL, "Binaural", volume=0.45, base_hz=200, beat_hz=10)],
                       description="Custom session")
        self.load_preset(blank)
        self.transport.dirty = True
        self._update_band()
        self.mixer.first_control().setFocus()

    def save_preset(self, name: str) -> None:
        if any(p.name.lower() == name.lower() for p in self.repo.builtin()):
            self.notify("Built-in presets can't be overwritten — choose another name")
            return
        existed = any(p.name.lower() == name.lower() for p in self.repo.user())
        d = self.transport.draft
        b = binaural_of(d)
        band = BrainwaveBand.for_frequency(b.beat_hz) if b else d.band
        preset = Preset(name, band, copy.deepcopy(d.channels), icon=d.icon,
                        description=d.description or "Custom session")
        self.repo.save(preset)
        d.name, d.band = name, band
        self.transport.dirty = False
        self.settings.last_preset = name
        self.refresh_library()
        self.mixer.end_save()
        self._update_band()
        self._save_settings()
        self.notify(f"Updated “{name}”" if existed else f"Saved “{name}” to My Presets")

    def begin_save(self) -> None:
        d = self.transport.draft
        is_user = any(p.name == d.name for p in self.repo.user())
        self.mixer.begin_save(d.name if is_user or d.name != "Untitled session" and not
                              any(p.name == d.name for p in self.repo.builtin())
                              else ("" if d.name == "Untitled session" else f"{d.name} (custom)"))

    def _preset_context(self, item, gpos) -> None:
        from .panels import ROLE_PRESET, ROLE_USER
        preset: Preset = item.data(ROLE_PRESET)
        m = QMenu(self)
        m.addAction("Load", lambda: self.load_preset(preset))
        m.addAction("Export…", lambda: self._export(preset))
        if item.data(ROLE_USER):
            m.addSeparator()
            m.addAction("Delete", lambda: self._delete(preset))
        m.exec(gpos)

    def _delete(self, preset: Preset) -> None:
        self.repo.delete(preset.name)
        self.refresh_library()
        self.notify(f"Deleted “{preset.name}”", action="Undo",
                    callback=lambda: (self.repo.save(preset), self.refresh_library(),
                                      self.notify(f"Restored “{preset.name}”")))

    def _export(self, preset: Preset | None = None) -> None:
        preset = preset or self.transport.draft
        path, _ = QFileDialog.getSaveFileName(self, "Export preset", f"{preset.name}.json",
                                              "NeuroSync preset (*.json)")
        if path:
            self.repo.export(preset, Path(path))
            self.notify(f"Exported “{preset.name}”")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import preset", "", "NeuroSync preset (*.json)")
        if not path:
            return
        try:
            p = self.repo.import_file(Path(path))
        except Exception:
            self.notify("That file isn't a valid NeuroSync preset")
            return
        self.refresh_library()
        self.notify(f"Imported “{p.name}”")

    # =====================================================================
    # live mixer edits
    # =====================================================================
    def _channel_changed(self, index: int, changes: dict) -> None:
        self.transport.update_channel(index, **changes)
        self._update_band()

    def _add_channel(self, key: str) -> None:
        if key in NOISE_NAMES:
            cfg = ChannelConfig(NOISE, NOISE_NAMES[key], variant=key, volume=0.3)
        elif key == "binaural":
            cfg = ChannelConfig(BINAURAL, "Binaural", volume=0.45)
        elif key.startswith(ASSET_PREFIX):
            sound = get_sound(key[len(ASSET_PREFIX):])
            cfg = ChannelConfig(SAMPLE, sound.name, path=key, volume=sound.default_volume)
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Add ambient sound", "",
                                                  "Audio (*.wav *.ogg *.flac)")
            if not path:
                return
            cfg = ChannelConfig(SAMPLE, Path(path).stem.replace("_", " ").title()[:18],
                                path=path, volume=0.4)
        try:
            self.transport.add_channel(cfg)
        except Exception as exc:
            self.notify(f"Couldn't open that sound: {exc}")
            return
        self.mixer.set_preset(self.transport.draft)
        self._update_band()
        self.notify(f"Added {cfg.name}")

    def _remove_channel(self, index: int) -> None:
        name = self.transport.draft.channels[index].name
        self.transport.remove_channel(index)
        self.mixer.set_preset(self.transport.draft)
        self._update_band()
        self.notify(f"Removed {name}")

    # =====================================================================
    # transport
    # =====================================================================
    def toggle_play(self) -> None:
        if self.transport.is_playing:
            self.transport.pause()
        else:
            if not self._ensure_player():
                return
            self.transport.play()
            self._timer_armed = self.transport.remaining_s is not None
        self._tick()

    def stop(self) -> None:
        self.transport.stop()
        self._tick()

    def _master_changed(self, v: int) -> None:
        g = TopBar.slider_to_gain(v)
        self.transport.set_master(g)
        self.topbar.master_pct.setText(f"{v}%")
        self.topbar.master.setAccessibleDescription(f"{v} percent of safe maximum")
        if v and self.topbar.mute.isChecked():
            self.topbar.mute.blockSignals(True); self.topbar.mute.setChecked(False)
            self.topbar.mute.blockSignals(False); self.topbar.set_theme(self.palette_, self.accent)
        if v:
            self.settings.master_volume = g
        self._save_settings_soon()

    def _mute_master(self, on: bool) -> None:
        if on:
            self._premute_volume = self.topbar.master.value()
            self.topbar.master.blockSignals(True); self.topbar.master.setValue(0)
            self.topbar.master.blockSignals(False)
            self.transport.set_master(0.0); self.topbar.master_pct.setText("0%")
        else:
            self.topbar.master.setValue(self._premute_volume or TopBar.gain_to_slider(self.settings.master_volume))
        self.topbar.set_theme(self.palette_, self.accent)

    def _nudge_volume(self, delta: int) -> None:
        self.topbar.master.setValue(self.topbar.master.value() + delta)

    def _timer_changed(self, minutes: float, fade: float) -> None:
        self.transport.set_timer(minutes or None, fade)
        self._timer_armed = bool(minutes)
        if fade:
            self.settings.fade_minutes = fade
            self._save_settings_soon()
        self._tick()

    # ---- audio device ---------------------------------------------------
    def _list_devices(self) -> list:
        try:
            from ..infra.audio_output import AudioOutputDeviceManager
            mgr = AudioOutputDeviceManager()
            wasapi = mgr.list_devices(wasapi_only=True)
            return wasapi or mgr.list_devices()
        except Exception:
            return []

    def _fill_devices(self) -> None:
        combo = self.topbar.device
        combo.blockSignals(True); combo.clear()
        combo.addItem(icon("device", "#9AA3AF", 16), "System default", None)
        for d in self._devices:
            combo.addItem(icon("device", "#9AA3AF", 16), d.name, d.index)
        idx = combo.findText(self.settings.device_name) if self.settings.device_name else 0
        combo.setCurrentIndex(max(0, idx))
        combo.blockSignals(False)

    def _device_changed(self, _i: int) -> None:
        name = self.topbar.device.currentText()
        self.settings.device_name = "" if self.topbar.device.currentIndex() == 0 else name
        self._save_settings()
        if self._player is not None:
            self._restart_player()
        self.notify(f"Output: {name}")

    def _default_player(self, render, device, exclusive):
        try:
            from ..infra.audio_output import LowLatencyPlayer
            player = LowLatencyPlayer(render, device=device, exclusive=exclusive)
            player.start()
            return player
        except Exception:
            from ..infra.audio_output import SimulatedPlayer
            player = SimulatedPlayer(render)
            player.start()
            self.notify("No audio output available — running silently")
            return player

    def _ensure_player(self) -> bool:
        if self._player is not None:
            return True
        try:
            self._player = self._player_factory(self.transport.render,
                                                self.topbar.device.currentData(),
                                                self.settings.exclusive_mode)
        except Exception as exc:
            self.notify(f"Couldn't open the audio device: {exc}")
            return False
        return True

    def _release_player(self) -> None:
        if self._player is not None:
            self._player.stop()
            self._player = None

    def _restart_player(self) -> None:
        self._release_player(); self._ensure_player()

    # ---- periodic UI sync (also the "session ended" watchdog) ------------
    def _tick(self) -> None:
        t = self.transport
        state = t.state
        playing = t.is_playing
        self.topbar.set_playing(playing)
        self.stage.orb.set_playing(state is SessionState.PLAYING)
        rem = t.remaining_s
        self.topbar.countdown.setText(_fmt_time(rem) if rem is not None and self._timer_armed else "")
        self.topbar.timer.setText("" if rem is None else "")

        if state is SessionState.PLAYING:
            msg = "Playing"
            if rem is not None:
                msg += f"  ·  {_fmt_time(rem)} remaining"
            self.stage.set_status(msg, "Space to pause")
        elif state is SessionState.FADING:
            self.stage.set_status("Fading out…", "")
        elif state is SessionState.PAUSED:
            self.stage.set_status("Paused", "Space to resume")
        else:
            self.stage.set_status("Ready", "Press Space or ▶ to begin  ·  F1 for shortcuts")

        if state is SessionState.STOPPED and self._player is not None:
            # Session over: release the audio device and go quiet (Workflow 3).
            self._release_player()
            if self._timer_armed:
                self.notify("Session complete — audio stopped")
                if self.tray and not self.isVisible():
                    self.tray.showMessage("NeuroSync", "Session complete", icon("orb", self.accent, 32), 3000)
            self._timer_armed = False
            if self._quitting:
                QApplication.quit()
        self._poll.setInterval(200 if playing else 1000)

        if self.tray:
            tip = f"NeuroSync — {t.draft.name}"
            if playing and rem is not None:
                tip += f" · {_fmt_time(rem)} left"
            self.tray.setToolTip(tip)
            self._tray_play.setText("Pause" if playing else "Play")

    # =====================================================================
    # menus, shortcuts, tray
    # =====================================================================
    def _build_menu(self) -> QMenu:
        m = QMenu(self)
        m.addAction(icon("save", "#9AA3AF", 16), "Save as preset…", self.begin_save, QKeySequence("Ctrl+S"))
        m.addAction(icon("plus", "#9AA3AF", 16), "New custom session", self.new_session, QKeySequence("Ctrl+N"))
        m.addAction("Import preset…", self._import)
        m.addAction("Export current preset…", self._export)
        m.addSeparator()
        self.act_hc = self._toggle(m, "High contrast", "high_contrast", self.apply_theme)
        self.act_rm = self._toggle(m, "Reduce motion", "reduce_motion", self.apply_theme)
        self.act_ex = self._toggle(m, "WASAPI exclusive mode", "exclusive_mode",
                                   lambda: self._player is not None and self._restart_player())
        self._toggle(m, "Keep playing in tray when closed", "close_to_tray", lambda: None)
        m.addSeparator()
        m.addAction(icon("keyboard", "#9AA3AF", 16), "Keyboard shortcuts", self.help.open, QKeySequence("F1"))
        m.addAction(icon("headphones", "#9AA3AF", 16), "Safety information", self._show_disclaimer)
        m.addSeparator()
        m.addAction("Quit", self.quit, QKeySequence("Ctrl+Q"))
        return m

    def _toggle(self, menu: QMenu, label: str, attr: str, then: Callable) -> QAction:
        a = menu.addAction(label); a.setCheckable(True); a.setChecked(getattr(self.settings, attr))

        def flip(on: bool) -> None:
            setattr(self.settings, attr, on); self._save_settings(); then()
        a.toggled.connect(flip)
        return a

    def _shortcuts(self) -> None:
        def sc(keys: str, fn: Callable) -> None:
            QShortcut(QKeySequence(keys), self, fn)
        sc("Space", self.toggle_play)
        sc("Ctrl+Space", self.stop)
        sc("Ctrl+S", self.begin_save)
        sc("Ctrl+N", self.new_session)
        sc("Ctrl+T", lambda: self.topbar.timer.showMenu())
        sc("Ctrl+Up", lambda: self._nudge_volume(5))
        sc("Ctrl+Down", lambda: self._nudge_volume(-5))
        sc("M", lambda: self.topbar.mute.toggle())
        sc("Ctrl+M", self.to_tray)
        sc("Ctrl+Shift+H", self.act_hc.toggle)
        sc("F1", self.help.open)
        sc("F6", self._cycle_region)
        sc("Ctrl+Q", self.quit)
        sc("Ctrl+F", lambda: self.library.search.setFocus())

    def _cycle_region(self) -> None:
        regions = [self.library.list, self.topbar.play, self.mixer.first_control()]
        fw = QApplication.focusWidget()
        cur = next((i for i, r in enumerate((self.library, self.topbar, self.mixer))
                    if fw is not None and (fw is r or r.isAncestorOf(fw))), -1)
        regions[(cur + 1) % len(regions)].setFocus(Qt.TabFocusReason)

    def _build_tray(self) -> QSystemTrayIcon | None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_play = QAction(self)
            return None
        tray = QSystemTrayIcon(icon("orb", self.accent, 32), self)
        menu = QMenu()
        menu.addAction("Show NeuroSync", self.restore_from_tray)
        self._tray_play = menu.addAction("Play", self.toggle_play)
        menu.addAction("Stop", self.stop)
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda r: self.restore_from_tray()
                               if r in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        tray.show()
        self._tray_menu = menu
        return tray

    def to_tray(self) -> None:
        if not self.tray:
            self.showMinimized(); return
        self.hide()
        if not self.settings.tray_hint_shown:
            self.tray.showMessage("NeuroSync is still running",
                                  "Playback continues here. Click the orb to come back.",
                                  icon("orb", self.accent, 32), 4000)
            self.settings.tray_hint_shown = True; self._save_settings()

    def restore_from_tray(self) -> None:
        self.showNormal(); self.raise_(); self.activateWindow()

    # =====================================================================
    # overlays, notifications, lifecycle
    # =====================================================================
    def _show_disclaimer(self) -> None:
        ov = DisclaimerOverlay(self.root, self.accent)
        ov.accepted.connect(self._disclaimer_accepted)
        ov.closed.connect(ov.deleteLater)
        self._set_interactive(False)
        ov.closed.connect(lambda: self._set_interactive(True))
        ov.open()
        self._disclaimer = ov

    def _disclaimer_accepted(self) -> None:
        self.settings.disclaimer_accepted = True
        self._save_settings()

    def _set_interactive(self, on: bool) -> None:
        for w in (self.topbar, self.library, self.stage, self.mixer):
            w.setEnabled(on)

    def notify(self, text: str, action: str | None = None, callback: Callable | None = None) -> None:
        self.toast.show_message(text, self.accent, action, callback)

    def _save_settings_soon(self) -> None:
        if not hasattr(self, "_save_timer"):
            self._save_timer = QTimer(self); self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_settings)
        self._save_timer.start(600)

    def _save_settings(self) -> None:
        try:
            self.settings.save(self.settings_dir)
        except OSError:
            pass

    def quit(self) -> None:
        """Quit honours the fade-out rule: hide immediately, fade audio, then exit."""
        self._quitting = True
        self._save_settings()
        if self.tray:
            self.tray.hide()
        self.hide()
        if self.transport.is_playing and self._player is not None:
            self._timer_armed = False
            self.transport.stop()
        else:
            self._release_player()
            QApplication.quit()

    def closeEvent(self, e) -> None:
        if not self._quitting and self.settings.close_to_tray and self.tray:
            e.ignore(); self.to_tray()
        else:
            e.ignore(); self.quit()
