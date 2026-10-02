"""The four regions of the main window: TopBar, PresetLibrary, CenterStage, MixerPanel."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QPushButton, QScrollArea, QSizePolicy, QSpinBox,
                               QStackedWidget, QStyle, QStyledItemDelegate, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction)

from ..domain.bands import BrainwaveBand
from ..domain.limits import (BASE_FREQ_MAX_HZ, BASE_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ,
                             BEAT_FREQ_MIN_HZ, MASTER_GAIN_MAX)
from ..domain.models import BINAURAL, NOISE, ChannelConfig, Preset
from .icons import icon, pixmap
from .theme import BAND_CATEGORY, BAND_COLORS, CATEGORY_ORDER, DARK, Palette, band_color
from .widgets import GlowSlider, OrbVisualizer


def _label(text: str = "", name: str | None = None, align=None) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    if align is not None:
        lbl.setAlignment(align)
    return lbl


def icon_button(name: str, tip: str, color: str = "#E9ECF1", size: int = 18,
                checkable: bool = False) -> QToolButton:
    b = QToolButton()
    b.setObjectName("IconButton")
    b.setIcon(icon(name, color, size)); b.setIconSize(QSize(size, size))
    b.setToolTip(tip); b.setAccessibleName(tip.split(" (")[0])
    b.setCheckable(checkable); b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.StrongFocus)
    return b


def preset_category(p: Preset, user: bool) -> str:
    return "My Presets" if user else (p.category or BAND_CATEGORY[p.band])


def binaural_of(p: Preset) -> ChannelConfig | None:
    return next((c for c in p.channels if c.kind == BINAURAL), None)


def describe(p: Preset) -> str:
    b = binaural_of(p)
    return f"{p.band.label} · {b.beat_hz:g} Hz" if b else p.band.label


# ===========================================================================
# Top bar
# ===========================================================================
class TimerPopover(QWidget):
    """Sleep timer: duration chips + custom minutes + optional fade-out length."""
    changed = Signal(float, float)   # minutes (0 = off), fade minutes (0 = minimum 3 s)
    CHOICES = (0, 15, 30, 45, 60, 90)

    def __init__(self, fade_minutes: float) -> None:
        super().__init__()
        self.setMinimumWidth(320)
        lay = QVBoxLayout(self); lay.setContentsMargins(14, 12, 14, 14); lay.setSpacing(10)
        lay.addWidget(_label("SLEEP TIMER", "SectionTitle"))
        chips = QHBoxLayout(); chips.setSpacing(6)
        self.group = QButtonGroup(self); self.group.setExclusive(True)
        for m in self.CHOICES:
            b = QPushButton("Off" if m == 0 else f"{m}m"); b.setObjectName("Chip")
            b.setCheckable(True); b.setAccessibleName("Timer off" if m == 0 else f"{m} minutes")
            self.group.addButton(b, m); chips.addWidget(b)
        self.group.button(0).setChecked(True)
        lay.addLayout(chips)

        row = QHBoxLayout()
        row.addWidget(_label("Custom", "Dim"))
        self.custom = QSpinBox(); self.custom.setRange(0, 720); self.custom.setSuffix(" min")
        self.custom.setSpecialValueText("—"); self.custom.setAccessibleName("Custom timer minutes")
        row.addWidget(self.custom); row.addStretch()
        lay.addLayout(row)

        frow = QHBoxLayout()
        self.fade_on = QCheckBox("Fade out over"); self.fade_on.setChecked(fade_minutes > 0)
        self.fade = QSpinBox(); self.fade.setRange(1, 30); self.fade.setSuffix(" min")
        self.fade.setValue(int(fade_minutes) or 5); self.fade.setAccessibleName("Fade-out minutes")
        frow.addWidget(self.fade_on); frow.addWidget(self.fade); frow.addStretch()
        lay.addLayout(frow)
        lay.addWidget(_label("Audio always fades for at least 3 seconds.", "Faint"))

        self.group.idClicked.connect(lambda m: (self.custom.blockSignals(True),
                                                self.custom.setValue(0),
                                                self.custom.blockSignals(False), self._emit()))
        self.custom.valueChanged.connect(self._custom_changed)
        self.fade_on.toggled.connect(self._emit); self.fade.valueChanged.connect(self._emit)

    def _custom_changed(self, v: int) -> None:
        if v:
            self.group.setExclusive(False)
            for b in self.group.buttons():
                b.setChecked(False)
            self.group.setExclusive(True)
        else:
            self.group.button(0).setChecked(True)
        self._emit()

    @property
    def minutes(self) -> float:
        return float(self.custom.value() or max(self.group.checkedId(), 0))

    @property
    def fade_minutes(self) -> float:
        if not self.fade_on.isChecked():
            return 0.0
        return float(min(self.fade.value(), self.minutes or self.fade.value()))

    def _emit(self) -> None:
        self.changed.emit(self.minutes, self.fade_minutes)


class TopBar(QFrame):
    def __init__(self, fade_minutes: float) -> None:
        super().__init__()
        self.setObjectName("TopBar"); self.setFixedHeight(76)
        self.setAccessibleName("Transport")
        lay = QHBoxLayout(self); lay.setContentsMargins(18, 10, 14, 10); lay.setSpacing(10)

        self.logo = QLabel(); self.logo.setPixmap(pixmap("orb", "#2DD4E8", 26, 2))
        self.logo.setAccessibleName("NeuroSync")
        word = QHBoxLayout(); word.setSpacing(0)
        word.addWidget(_label("Neuro", "Wordmark")); word.addWidget(_label("Sync", "WordmarkAccent"))
        lay.addWidget(self.logo); lay.addLayout(word); lay.addSpacing(10)
        lay.addStretch(1)

        # transport cluster (centre)
        self.stop = icon_button("stop", "Stop with fade-out (Ctrl+Space)")
        self.play = QPushButton(); self.play.setObjectName("PlayButton")
        self.play.setFixedSize(52, 52); self.play.setIconSize(QSize(22, 22))
        self.play.setCursor(Qt.PointingHandCursor); self.play.setAccessibleName("Play")
        self.play.setToolTip("Play / Pause (Space)")
        self.timer = QToolButton(); self.timer.setObjectName("IconButton")
        self.timer.setIconSize(QSize(18, 18)); self.timer.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.timer.setPopupMode(QToolButton.InstantPopup); self.timer.setCursor(Qt.PointingHandCursor)
        self.timer.setToolTip("Sleep timer (Ctrl+T)"); self.timer.setAccessibleName("Sleep timer")
        self.timer_menu = QMenu(self.timer)
        self.popover = TimerPopover(fade_minutes)
        act = QWidgetAction(self.timer_menu); act.setDefaultWidget(self.popover)
        self.timer_menu.addAction(act)
        self.timer.setMenu(self.timer_menu)
        self.countdown = _label("", "Countdown")
        self.countdown.setMinimumWidth(64)
        lay.addWidget(self.stop); lay.addWidget(self.play); lay.addWidget(self.timer)
        lay.addWidget(self.countdown)
        lay.addStretch(1)

        # output cluster (right)
        self.mute = icon_button("volume", "Mute master (M)", checkable=True)
        self.master = GlowSlider(Qt.Horizontal); self.master.setRange(0, 100)
        self.master.setFixedWidth(150); self.master.setPageStep(10)
        self.master.setAccessibleName("Master volume")
        self.master.detents = [50]
        self.master_pct = _label("50%", "StripValue"); self.master_pct.setFixedWidth(42)
        self.device = QComboBox(); self.device.setAccessibleName("Output device")
        self.device.setToolTip("Output device"); self.device.setMaximumWidth(230)
        self.device.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.device.setMinimumContentsLength(16)
        self.more = icon_button("more", "Menu")
        self.more.setPopupMode(QToolButton.InstantPopup)
        self.to_tray = icon_button("minimize", "Minimize to tray (Ctrl+M)")
        for w in (self.mute, self.master, self.master_pct, self.device, self.more, self.to_tray):
            lay.addWidget(w)

    # master slider shows 0-100 % of the *safe* range (100 % == 0.85 gain)
    @staticmethod
    def gain_to_slider(g: float) -> int:
        return round(g / MASTER_GAIN_MAX * 100)

    @staticmethod
    def slider_to_gain(v: int) -> float:
        return v / 100 * MASTER_GAIN_MAX

    def set_theme(self, palette: Palette, accent: QColor) -> None:
        self.master.set_theme(palette, accent)
        self.logo.setPixmap(pixmap("orb", accent if palette.glass else QColor("#FFFFFF"), 26, 2))
        fg = palette.text
        self.stop.setIcon(icon("stop", fg, 18)); self.more.setIcon(icon("more", fg, 18))
        self.to_tray.setIcon(icon("minimize", fg, 18))
        self.timer.setIcon(icon("timer", fg, 18))
        self.mute.setIcon(icon("mute" if self.mute.isChecked() else "volume", fg, 18))
        self._fg = fg

    def set_playing(self, playing: bool) -> None:
        self.play.setIcon(icon("pause" if playing else "play", "#0B0C0E", 22))
        self.play.setAccessibleName("Pause" if playing else "Play")


# ===========================================================================
# Preset library (left sidebar)
# ===========================================================================
ROLE_PRESET, ROLE_KIND, ROLE_USER = Qt.UserRole, Qt.UserRole + 1, Qt.UserRole + 2


class PresetDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.palette: Palette = DARK
        self.accent = QColor("#2DD4E8")
        self.current_name = ""

    def sizeHint(self, option, index) -> QSize:
        return QSize(200, 34 if index.data(ROLE_KIND) == "header" else 50)

    def paint(self, p: QPainter, option, index) -> None:
        p.save(); p.setRenderHint(QPainter.Antialiasing)
        r: QRect = option.rect
        pal = self.palette
        if index.data(ROLE_KIND) == "header":
            f = QFont(option.font); f.setPointSizeF(7.8); f.setBold(True)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 1.6)
            p.setFont(f); p.setPen(QColor(pal.text_faint if pal.glass else pal.text))
            p.drawText(r.adjusted(12, 10, 0, 0), Qt.AlignLeft | Qt.AlignVCenter,
                       index.data(Qt.DisplayRole).upper())
            p.restore(); return

        preset: Preset = index.data(ROLE_PRESET)
        selected = option.state & QStyle.State_Selected
        hovered = option.state & QStyle.State_MouseOver
        is_current = preset.name == self.current_name
        box = r.adjusted(2, 1, -2, -1)
        if selected or hovered or is_current:
            if pal.glass:
                c = QColor(self.accent); c.setAlphaF(0.15 if (selected or is_current) else 0.0)
                bg = c if (selected or is_current) else QColor(255, 255, 255, 18)
                p.setPen(Qt.NoPen); p.setBrush(bg)
            else:
                p.setPen(QPen(QColor("#FFFF00"), 2)); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(box, 10, 10)
        if option.state & QStyle.State_HasFocus and self.parent().hasFocus():
            p.setPen(QPen(QColor(pal.focus or self.accent), 2)); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(box.adjusted(1, 1, -1, -1), 9, 9)
        if is_current:   # glowing accent tab
            p.setPen(Qt.NoPen); p.setBrush(self.accent if pal.glass else QColor("#FFFF00"))
            p.drawRoundedRect(QRect(box.left(), box.top() + 12, 3, box.height() - 24), 1.5, 1.5)

        dot = QColor(BAND_COLORS[preset.band])
        p.setPen(Qt.NoPen)
        if pal.glass:
            halo = QColor(dot); halo.setAlphaF(0.25); p.setBrush(halo)
            p.drawEllipse(box.left() + 18 - 7, box.center().y() - 7, 14, 14)
        p.setBrush(dot); p.drawEllipse(box.left() + 18 - 4, box.center().y() - 4, 8, 8)

        f = QFont(option.font); f.setPointSizeF(10); f.setWeight(QFont.Medium)
        p.setFont(f); p.setPen(QColor(pal.text))
        p.drawText(box.adjusted(36, 7, -8, -box.height() // 2), Qt.AlignLeft | Qt.AlignVCenter,
                   preset.name)
        f.setPointSizeF(8.5); f.setWeight(QFont.Normal)
        p.setFont(f); p.setPen(QColor(pal.text_dim))
        p.drawText(box.adjusted(36, box.height() // 2, -8, -6), Qt.AlignLeft | Qt.AlignVCenter,
                   describe(preset))
        p.restore()


class PresetLibrary(QFrame):
    presetChosen = Signal(object)            # Preset
    newRequested = Signal()
    contextRequested = Signal(object, object)  # Preset, global QPoint

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("GlassPanel"); self.setFixedWidth(258)
        self.setAccessibleName("Preset library")
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 16, 12, 12); lay.setSpacing(10)
        head = QHBoxLayout(); head.setContentsMargins(6, 0, 0, 0)
        head.addWidget(_label("LIBRARY", "SectionTitle")); head.addStretch()
        self.new_btn = icon_button("plus", "New custom session (Ctrl+N)", size=16)
        head.addWidget(self.new_btn)
        lay.addLayout(head)
        self.search = QLineEdit(); self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("Search presets"); self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search presets")
        lay.addWidget(self.search)
        self.list = QListWidget(); self.list.setAccessibleName("Presets")
        self.list.setMouseTracking(True); self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.delegate = PresetDelegate(self.list); self.list.setItemDelegate(self.delegate)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        lay.addWidget(self.list, 1)
        self.hint = _label("Enter to load · Right-click to manage", "Faint")
        self.hint.setAlignment(Qt.AlignCenter); lay.addWidget(self.hint)

        self.new_btn.clicked.connect(self.newRequested)
        self.list.itemClicked.connect(self._chosen); self.list.itemActivated.connect(self._chosen)
        self.search.textChanged.connect(self._filter)
        self.list.customContextMenuRequested.connect(self._context)

    def populate(self, builtin: list[Preset], user: list[Preset], current: str) -> None:
        self.list.clear()
        groups: dict[str, list[tuple[Preset, bool]]] = {}
        for p in builtin:
            groups.setdefault(preset_category(p, False), []).append((p, False))
        for p in user:
            groups.setdefault("My Presets", []).append((p, True))
        order = CATEGORY_ORDER + [g for g in groups if g not in CATEGORY_ORDER and g != "My Presets"] + ["My Presets"]
        for g in order:
            if g not in groups:
                continue
            h = QListWidgetItem(g); h.setData(ROLE_KIND, "header"); h.setFlags(Qt.NoItemFlags)
            self.list.addItem(h)
            for p, is_user in groups[g]:
                it = QListWidgetItem(p.name)
                it.setData(ROLE_KIND, "preset"); it.setData(ROLE_PRESET, p); it.setData(ROLE_USER, is_user)
                it.setData(Qt.AccessibleTextRole, f"{p.name}, {describe(p).replace('Hz', 'hertz')}")
                it.setData(Qt.AccessibleDescriptionRole, p.description)
                it.setToolTip(p.description)
                self.list.addItem(it)
        self.set_current(current)
        self._filter(self.search.text())

    def set_current(self, name: str) -> None:
        self.delegate.current_name = name
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(ROLE_KIND) == "preset" and it.data(ROLE_PRESET).name == name:
                self.list.setCurrentItem(it)
        self.list.viewport().update()

    def set_theme(self, palette: Palette, accent: QColor) -> None:
        self.delegate.palette, self.delegate.accent = palette, QColor(accent)
        self.new_btn.setIcon(icon("plus", palette.text, 16))
        self.list.viewport().update()

    def _chosen(self, it: QListWidgetItem) -> None:
        if it.data(ROLE_KIND) == "preset":
            self.presetChosen.emit(it.data(ROLE_PRESET))

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        header = None; visible_in_group = False
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(ROLE_KIND) == "header":
                if header is not None:
                    header.setHidden(not visible_in_group)
                header, visible_in_group = it, False
                continue
            p: Preset = it.data(ROLE_PRESET)
            hit = not text or text in p.name.lower() or text in p.band.label.lower()
            it.setHidden(not hit); visible_in_group |= hit
        if header is not None:
            header.setHidden(not visible_in_group)

    def _context(self, pos) -> None:
        it = self.list.itemAt(pos)
        if it is not None and it.data(ROLE_KIND) == "preset":
            self.contextRequested.emit(it, self.list.viewport().mapToGlobal(pos))


# ===========================================================================
# Center stage
# ===========================================================================
class CenterStage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("Now playing")
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 22, 8, 18); lay.setSpacing(6)
        chip_row = QHBoxLayout(); chip_row.addStretch()
        self.chip = _label("ALPHA", "BandChip"); chip_row.addWidget(self.chip); chip_row.addStretch()
        lay.addLayout(chip_row)
        lay.addSpacing(6)
        self.title = _label("", "PresetTitle", Qt.AlignCenter)
        self.meta = _label("", "PresetMeta", Qt.AlignCenter)
        lay.addWidget(self.title); lay.addWidget(self.meta)
        self.orb = OrbVisualizer()
        self.orb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.orb, 1)
        self.status = _label("", "Dim", Qt.AlignCenter)
        self.hint = _label("", "Faint", Qt.AlignCenter)
        lay.addWidget(self.status); lay.addWidget(self.hint)

    def show_preset(self, preset: Preset, band: BrainwaveBand, dirty: bool) -> None:
        self.chip.setText(f"{band.label.upper()}  ·  {band.low_hz:g}–{band.high_hz:g} Hz")
        self.title.setText(preset.name + ("  ·  edited" if dirty else ""))
        b = binaural_of(preset)
        self.meta.setText(f"{b.base_hz:g} Hz carrier   ·   {b.beat_hz:g} Hz beat" if b
                          else "Ambient only")
        self.orb.set_beat(b.beat_hz if b else None)

    def set_status(self, text: str, hint: str = "") -> None:
        self.status.setText(text); self.hint.setText(hint)


# ===========================================================================
# Mixer (right panel)
# ===========================================================================
class ChannelStrip(QFrame):
    """One vertical fader with value readout, optional band label, mute, pan and remove."""
    valueChanged = Signal(float)
    muteToggled = Signal(bool)
    panChanged = Signal(float)
    removeRequested = Signal()

    def __init__(self, title: str, icon_name: str, lo: float, hi: float, step: float,
                 value: float, fmt: Callable[[float], str], spoken: Callable[[float], str],
                 generator: bool = False, muted: bool | None = None, pan: float | None = None,
                 removable: bool = False, detents: tuple[float, ...] = (),
                 band_of: Callable[[float], BrainwaveBand] | None = None) -> None:
        super().__init__()
        self.setObjectName("Strip"); self.setProperty("generator", generator)
        self.setFixedWidth(86)
        self._step, self._fmt, self._spoken, self._band_of = step, fmt, spoken, band_of
        self._title = title
        lay = QVBoxLayout(self); lay.setContentsMargins(6, 10, 6, 10); lay.setSpacing(6)
        lay.setAlignment(Qt.AlignHCenter)

        top = QHBoxLayout(); top.setSpacing(2)
        self.icon = QLabel(); self.icon_name = icon_name
        top.addStretch(); top.addWidget(self.icon)
        self.remove = None
        if removable:
            self.remove = icon_button("close", f"Remove {title}", size=12)
            self.remove.setFixedSize(20, 20)
            self.remove.clicked.connect(self.removeRequested)
            top.addWidget(self.remove)
        top.addStretch()
        lay.addLayout(top)
        self.name = _label(title, "StripLabel", Qt.AlignCenter)
        self.name.setWordWrap(True)
        lay.addWidget(self.name)
        self.value_lbl = _label("", "StripValue", Qt.AlignCenter)
        lay.addWidget(self.value_lbl)
        self.band_lbl = _label("", "StripBand", Qt.AlignCenter) if band_of else None
        if self.band_lbl:
            lay.addWidget(self.band_lbl)

        self.slider = GlowSlider(Qt.Vertical)
        self.slider.setRange(round(lo / step), round(hi / step))
        self.slider.setPageStep(max(1, (self.slider.maximum() - self.slider.minimum()) // 10))
        self.slider.setValue(round(value / step))
        self.slider.detents = [round(d / step) for d in detents]
        self.slider.setAccessibleName(title)
        lay.addWidget(self.slider, 1, Qt.AlignHCenter)

        self.pan = None
        if pan is not None:
            self.pan = GlowSlider(Qt.Horizontal); self.pan.setRange(-100, 100)
            self.pan.setValue(round(pan * 100)); self.pan.setFixedWidth(72)
            self.pan.setMinimumHeight(24); self.pan.detents = [0]
            self.pan.setAccessibleName(f"{title} pan")
            self.pan.setToolTip("Pan (double-click to centre)")
            self.pan.valueChanged.connect(lambda v: self.panChanged.emit(v / 100))
            self.pan.mouseDoubleClickEvent = lambda e: self.pan.setValue(0)
            lay.addWidget(self.pan, 0, Qt.AlignHCenter)

        self.mute = None
        if muted is not None:
            self.mute = icon_button("volume", f"Mute {title}", size=16, checkable=True)
            self.mute.setChecked(muted)
            self.mute.toggled.connect(self._mute_toggled)
            lay.addWidget(self.mute, 0, Qt.AlignHCenter)

        self.slider.valueChanged.connect(self._changed)
        self._refresh(self.value)

    @property
    def value(self) -> float:
        return round(self.slider.value() * self._step, 6)

    def _changed(self, _v: int) -> None:
        self._refresh(self.value)
        self.valueChanged.emit(self.value)

    def _mute_toggled(self, on: bool) -> None:
        self.slider.setEnabled(not on)
        self._apply_icons()
        self.muteToggled.emit(on)

    def _refresh(self, v: float) -> None:
        self.value_lbl.setText(self._fmt(v))
        desc = self._spoken(v)
        if self.band_lbl:
            band = self._band_of(v)
            self.band_lbl.setText(band.label.upper())
            glass = getattr(self, "_palette", DARK).glass
            self.band_lbl.setStyleSheet(f"color: {BAND_COLORS[band] if glass else '#FFFF00'};")
            desc += f", {band.label} band"
        self.slider.setAccessibleDescription(desc)

    def set_theme(self, palette: Palette, accent: QColor) -> None:
        self._palette = palette
        self.slider.set_theme(palette, accent)
        if self.pan:
            self.pan.set_theme(palette, accent)
        if self.remove:
            self.remove.setIcon(icon("close", palette.text_dim, 12))
        self._accent = accent
        self._apply_icons()

    def _apply_icons(self) -> None:
        pal = getattr(self, "_palette", DARK)
        self.icon.setPixmap(pixmap(self.icon_name, getattr(self, "_accent", QColor("#2DD4E8"))
                                   if pal.glass else QColor("#FFFFFF"), 18, 2))
        if self.mute:
            muted = self.mute.isChecked()
            self.mute.setIcon(icon("mute" if muted else "volume",
                                   pal.danger if muted else pal.text_dim, 16))


class MixerPanel(QFrame):
    channelChanged = Signal(int, dict)
    addRequested = Signal(str)          # "pink"|"brown"|"white"|"file"|"binaural"|"asset:<id>"
    removeRequested = Signal(int)
    saveRequested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("GlassPanel"); self.setFixedWidth(418)
        self.setAccessibleName("Mixer")
        self._palette, self._accent = DARK, QColor("#2DD4E8")
        self.strips: list[ChannelStrip] = []
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 14, 16, 16); lay.setSpacing(12)

        # header: title + Save, morphing into an inline name editor (no pop-up dialogs)
        self.header = QStackedWidget(); self.header.setFixedHeight(38)
        view = QWidget(); hv = QHBoxLayout(view); hv.setContentsMargins(4, 0, 0, 0)
        hv.addWidget(_label("MIXER", "SectionTitle"))
        self.dirty_dot = _label("●", "Faint"); self.dirty_dot.setToolTip("Unsaved changes")
        hv.addWidget(self.dirty_dot); hv.addStretch()
        self.save_btn = QPushButton("Save as preset"); self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setToolTip("Save as preset (Ctrl+S)")
        hv.addWidget(self.save_btn)
        edit = QWidget(); he = QHBoxLayout(edit); he.setContentsMargins(0, 0, 0, 0); he.setSpacing(6)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Preset name")
        self.name_edit.setAccessibleName("New preset name"); self.name_edit.setMaxLength(48)
        self.confirm = QPushButton("Save"); self.confirm.setObjectName("Primary")
        self.cancel = icon_button("close", "Cancel (Esc)", size=14)
        he.addWidget(self.name_edit, 1); he.addWidget(self.confirm); he.addWidget(self.cancel)
        self.header.addWidget(view); self.header.addWidget(edit)
        lay.addWidget(self.header)

        lay.addWidget(_label("CUSTOM GENERATOR", "SectionTitle"))
        self.gen_row = QHBoxLayout(); self.gen_row.setSpacing(8)
        gen_wrap = QWidget(); gen_wrap.setLayout(self.gen_row); gen_wrap.setMinimumHeight(300)
        lay.addWidget(gen_wrap, 1)

        div = QFrame(); div.setObjectName("Divider"); lay.addWidget(div)
        amb_head = QHBoxLayout()
        amb_head.addWidget(_label("AMBIENCE", "SectionTitle")); amb_head.addStretch()
        self.add_btn = QToolButton(); self.add_btn.setObjectName("IconButton")
        self.add_btn.setText(" Add sound"); self.add_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.add_btn.setPopupMode(QToolButton.InstantPopup); self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setAccessibleName("Add ambient sound")
        menu = QMenu(self.add_btn)
        for label, key, ic in (("Pink noise", "pink", "noise"), ("Brown noise", "brown", "noise"),
                               ("White noise", "white", "noise")):
            menu.addAction(icon(ic, "#9AA3AF", 16), label, lambda k=key: self.addRequested.emit(k))
        from ..assets import ASSET_PREFIX, catalog
        category = None
        for sound in catalog():                       # bundled ambience, grouped by category
            if sound.category != category:
                category = sound.category
                menu.addSection(category)
            act = menu.addAction(icon("wave", "#9AA3AF", 16), sound.name,
                                 lambda sid=sound.id: self.addRequested.emit(ASSET_PREFIX + sid))
            act.setToolTip(sound.description)
        menu.addSeparator()
        menu.addAction(icon("file", "#9AA3AF", 16), "Sound file (.wav, .ogg)…",
                       lambda: self.addRequested.emit("file"))
        self.add_btn.setMenu(menu)
        amb_head.addWidget(self.add_btn)
        lay.addLayout(amb_head)

        self.amb_scroll = QScrollArea(); self.amb_scroll.setWidgetResizable(True)
        self.amb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.amb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.amb_inner = QWidget(); self.amb_row = QHBoxLayout(self.amb_inner)
        self.amb_row.setContentsMargins(0, 0, 0, 4); self.amb_row.setSpacing(8)
        self.amb_scroll.setWidget(self.amb_inner); self.amb_scroll.setMinimumHeight(290)
        lay.addWidget(self.amb_scroll, 1)

        self.save_btn.clicked.connect(self.begin_save)
        self.confirm.clicked.connect(self._confirm_save)
        self.name_edit.returnPressed.connect(self._confirm_save)
        self.cancel.clicked.connect(self.end_save)

    # --- inline save -------------------------------------------------------
    def begin_save(self, suggested: str = "") -> None:
        if isinstance(suggested, str) and suggested:
            self.name_edit.setText(suggested)
        self.header.setCurrentIndex(1)
        self.name_edit.setFocus(); self.name_edit.selectAll()

    def end_save(self) -> None:
        self.header.setCurrentIndex(0); self.save_btn.setFocus()

    def _confirm_save(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            self.saveRequested.emit(name)

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Escape and self.header.currentIndex() == 1:
            self.end_save()
        else:
            super().keyPressEvent(e)

    def set_dirty(self, dirty: bool) -> None:
        self.dirty_dot.setVisible(dirty)
        self.save_btn.setObjectName("Primary" if dirty else "")
        self.save_btn.style().unpolish(self.save_btn); self.save_btn.style().polish(self.save_btn)

    # --- strips ----------------------------------------------------------------
    def set_preset(self, preset: Preset) -> None:
        for s in self.strips:
            s.setParent(None); s.deleteLater()
        self.strips.clear()
        while self.gen_row.count():
            w = self.gen_row.takeAt(0).widget()
            if w:
                w.setParent(None); w.deleteLater()
        while self.amb_row.count():
            w = self.amb_row.takeAt(0).widget()
            if w:
                w.setParent(None); w.deleteLater()

        gen_index = next((i for i, c in enumerate(preset.channels) if c.kind == BINAURAL), None)
        if gen_index is None:
            ghost = QPushButton("＋  Add binaural tone"); ghost.setObjectName("Ghost")
            ghost.setMinimumHeight(120); ghost.clicked.connect(lambda: self.addRequested.emit("binaural"))
            self.gen_row.addWidget(ghost)
        else:
            c = preset.channels[gen_index]
            base = ChannelStrip("Base", "wave", BASE_FREQ_MIN_HZ, BASE_FREQ_MAX_HZ, 1, c.base_hz,
                                lambda v: f"{v:.0f} Hz", lambda v: f"{v:.0f} hertz carrier",
                                generator=True)
            beat = ChannelStrip("Beat", "orb", BEAT_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ, 0.1, c.beat_hz,
                                lambda v: f"{v:.1f} Hz", lambda v: f"{v:.1f} hertz beat",
                                generator=True, detents=(4, 8, 14, 30),
                                band_of=BrainwaveBand.for_frequency)
            tone = ChannelStrip("Tone level", "headphones", 0, 1, 0.01, c.volume,
                                lambda v: f"{v * 100:.0f}%", lambda v: f"{v * 100:.0f} percent",
                                generator=True, muted=c.muted)
            base.valueChanged.connect(lambda v, i=gen_index: self.channelChanged.emit(i, {"base_hz": v}))
            beat.valueChanged.connect(lambda v, i=gen_index: self.channelChanged.emit(i, {"beat_hz": v}))
            tone.valueChanged.connect(lambda v, i=gen_index: self.channelChanged.emit(i, {"volume": v}))
            tone.muteToggled.connect(lambda m, i=gen_index: self.channelChanged.emit(i, {"muted": m}))
            for s in (base, beat, tone):
                self.gen_row.addWidget(s); self.strips.append(s)
            self.gen_row.addStretch()
            tip = _label("Beat = right ear − left ear.\nKeep base 100–400 Hz\nfor the clearest beat.", "Faint")
            tip.setWordWrap(True); tip.setMaximumWidth(110); tip.setAlignment(Qt.AlignTop)
            self.gen_row.addWidget(tip, 0, Qt.AlignTop)

        for i, c in enumerate(preset.channels):
            if i == gen_index:
                continue
            ic = ("noise" if c.kind == NOISE else
                  "wave" if c.kind == BINAURAL or c.path.startswith("asset:") else "file")
            s = ChannelStrip(c.name, ic, 0, 1, 0.01, c.volume, lambda v: f"{v * 100:.0f}%",
                             lambda v: f"{v * 100:.0f} percent", muted=c.muted, pan=c.pan,
                             removable=True)
            s.valueChanged.connect(lambda v, i=i: self.channelChanged.emit(i, {"volume": v}))
            s.muteToggled.connect(lambda m, i=i: self.channelChanged.emit(i, {"muted": m}))
            s.panChanged.connect(lambda v, i=i: self.channelChanged.emit(i, {"pan": v}))
            s.removeRequested.connect(lambda i=i: self.removeRequested.emit(i))
            self.amb_row.addWidget(s); self.strips.append(s)
        if not any(c.kind != BINAURAL or i != gen_index for i, c in enumerate(preset.channels)):
            empty = _label("No ambience yet.\nAdd rain, pink or brown noise\nto mask distractions.", "Faint",
                           Qt.AlignCenter)
            self.amb_row.addWidget(empty, 1)
        self.amb_row.addStretch()
        self.set_theme(self._palette, self._accent)

    def first_control(self) -> QWidget:
        return self.strips[0].slider if self.strips else self.add_btn

    def set_theme(self, palette: Palette, accent: QColor) -> None:
        self._palette, self._accent = palette, QColor(accent)
        for s in self.strips:
            s.set_theme(palette, accent)
        self.add_btn.setIcon(icon("plus", palette.text, 16))
        self.cancel.setIcon(icon("close", palette.text_dim, 14))
