"""Custom-painted widgets: GlowSlider, OrbVisualizer, AuroraBackground, Toast, Overlay."""
from __future__ import annotations

import math
import time
from typing import Callable

from PySide6.QtCore import (QEasingCurve, QEvent, QPointF, QRectF, Qt, QTimer,
                            QVariantAnimation, Signal)
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

from .theme import DARK, Palette


def _anim(owner: QWidget, start, end, ms: int, on_value: Callable,
          curve=QEasingCurve.OutCubic, on_done: Callable | None = None) -> QVariantAnimation:
    a = QVariantAnimation(owner)
    a.setStartValue(start); a.setEndValue(end); a.setDuration(ms); a.setEasingCurve(curve)
    a.valueChanged.connect(on_value)
    if on_done:
        a.finished.connect(on_done)
    a.start(QVariantAnimation.DeleteWhenStopped)
    return a


# ---------------------------------------------------------------------------
class GlowSlider(QSlider):
    """QSlider with a painted glass track, glowing handle and 'haptic' detent pulses.

    Keeps all native QSlider behaviour (keyboard, wheel, accessibility); only
    painting and click-to-position are replaced. Crossing a value in `detents`
    (e.g. a brainwave band boundary) fires a brief halo pulse.
    """
    R = 9.0  # handle radius

    def __init__(self, orientation=Qt.Vertical, parent: QWidget | None = None) -> None:
        super().__init__(orientation, parent)
        self._accent = QColor("#2DD4E8")
        self._palette: Palette = DARK
        self._hover = self._press = self._pulse = 0.0
        self._anims: dict[str, QVariantAnimation] = {}
        self.detents: list[int] = []
        self._last_value = self.value()
        self.setFocusPolicy(Qt.StrongFocus)
        self.valueChanged.connect(self._check_detent)
        if orientation == Qt.Vertical:
            self.setMinimumSize(34, 120)
        else:
            self.setMinimumSize(100, 28)

    def set_theme(self, palette: Palette, accent: QColor) -> None:
        self._palette, self._accent = palette, QColor(accent)
        self.update()

    # --- animation plumbing ---
    def _animate(self, attr: str, target: float, ms: int = 160) -> None:
        old = self._anims.pop(attr, None)
        if old is not None:
            old.stop()

        def setv(v, attr=attr):
            setattr(self, attr, float(v)); self.update()
        self._anims[attr] = _anim(self, getattr(self, attr), target, ms, setv)

    def _check_detent(self, v: int) -> None:
        lo, hi = sorted((self._last_value, v))
        if any(lo < d <= hi for d in self.detents):
            self._pulse = 1.0
            self._animate("_pulse", 0.0, 420)
        self._last_value = v

    # --- geometry ---
    def _track(self) -> tuple[QPointF, QPointF]:
        r = self.rect()
        m = self.R + 3
        if self.orientation() == Qt.Vertical:
            x = r.center().x() + 0.5
            return QPointF(x, r.bottom() - m), QPointF(x, r.top() + m)
        y = r.center().y() + 0.5
        return QPointF(r.left() + m, y), QPointF(r.right() - m, y)

    def _frac(self, value: int) -> float:
        span = self.maximum() - self.minimum()
        return (value - self.minimum()) / span if span else 0.0

    def _point(self, frac: float) -> QPointF:
        a, b = self._track()
        return a + (b - a) * frac

    def _value_at(self, pos: QPointF) -> int:
        a, b = self._track()
        if self.orientation() == Qt.Vertical:
            frac = (a.y() - pos.y()) / max(1.0, a.y() - b.y())
        else:
            frac = (pos.x() - a.x()) / max(1.0, b.x() - a.x())
        frac = min(1.0, max(0.0, frac))
        return round(self.minimum() + frac * (self.maximum() - self.minimum()))

    # --- input ---
    def mousePressEvent(self, e) -> None:
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        self.setFocus(Qt.MouseFocusReason)
        self.setSliderDown(True)
        self.setValue(self._value_at(e.position()))
        self._animate("_press", 1.0, 120)
        e.accept()

    def mouseMoveEvent(self, e) -> None:
        if self.isSliderDown():
            self.setValue(self._value_at(e.position()))
            e.accept()

    def mouseReleaseEvent(self, e) -> None:
        if self.isSliderDown():
            self.setSliderDown(False)
            self._animate("_press", 0.0, 220)
            e.accept()

    def enterEvent(self, e) -> None:
        self._animate("_hover", 1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._animate("_hover", 0.0, 260)
        super().leaveEvent(e)

    # --- paint ---
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = self._palette
        acc = QColor(self._accent if pal.glass else QColor("#FFFF00"))
        if not self.isEnabled():
            acc.setAlphaF(0.35)
        a, b = self._track()
        frac = self._frac(self.value())
        h = self._point(frac)

        # track
        track_pen = QPen(QColor(255, 255, 255, 22 if pal.glass else 255), 6, Qt.SolidLine, Qt.RoundCap)
        if not pal.glass:
            track_pen.setWidthF(2)
        p.setPen(track_pen); p.drawLine(a, b)

        # detent ticks
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.2))
        for d in self.detents:
            t = self._point(self._frac(d))
            if self.orientation() == Qt.Vertical:
                p.drawLine(QPointF(t.x() - 9, t.y()), QPointF(t.x() - 6, t.y()))
            else:
                p.drawLine(QPointF(t.x(), t.y() + 6), QPointF(t.x(), t.y() + 9))

        # filled portion (gradient from dim to full accent)
        if frac > 0.001:
            g = QLinearGradient(a, h)
            dim = QColor(acc); dim.setAlphaF(acc.alphaF() * 0.35)
            g.setColorAt(0, dim); g.setColorAt(1, acc)
            p.setPen(QPen(QBrush(g), 6, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(a, h)

        # halo: hover / press / detent pulse
        energy = 0.35 * self._hover + 0.5 * self._press + 0.9 * self._pulse
        if energy > 0.01 and pal.glass:
            rad = self.R * (1.8 + 0.7 * self._press + 1.4 * self._pulse)
            rg = QRadialGradient(h, rad)
            c0 = QColor(acc); c0.setAlphaF(min(1.0, 0.45 * energy))
            c1 = QColor(acc); c1.setAlphaF(0.0)
            rg.setColorAt(0, c0); rg.setColorAt(1, c1)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(rg))
            p.drawEllipse(h, rad, rad)

        # handle
        r = self.R * (1.0 + 0.14 * self._press)
        p.setPen(QPen(acc, 2.2))
        p.setBrush(QColor("#F4F6F9") if pal.glass else QColor("#000000"))
        p.drawEllipse(h, r, r)
        p.setPen(Qt.NoPen); p.setBrush(acc)
        p.drawEllipse(h, r * 0.32, r * 0.32)

        # keyboard focus ring
        if self.hasFocus():
            p.setPen(QPen(QColor(pal.focus or acc), 2, Qt.DotLine))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(h, r + 4.5, r + 4.5)
        p.end()


# ---------------------------------------------------------------------------
def visual_pulse_hz(beat_hz: float, ceiling: float = 1.25) -> float:
    """Fold the beat down by octaves into a calm, non-flashing visual rate.

    40 Hz gamma must never become a 40 Hz flicker (photosensitivity). Halving
    keeps the pulse rhythmically locked to the audio beat.
    """
    hz = max(beat_hz, 0.05)
    while hz > ceiling:
        hz /= 2.0
    return hz


class OrbVisualizer(QWidget):
    """Softly breathing orb with outward ripples, locked to the beat (octave-folded)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor("#2DD4E8")
        self._energy = 0.0         # 0 idle -> 1 playing, animated
        self._beat = 10.0
        self._playing = False
        self.reduce_motion = False
        self._glass = True
        self._t0 = time.monotonic()
        self._frame = QTimer(self)
        self._frame.setInterval(33)            # ~30 fps: smooth, cheap
        self._frame.timeout.connect(self.update)
        self.setMinimumSize(260, 260)
        self.setAccessibleName("Visualizer")
        self.setFocusPolicy(Qt.NoFocus)

    @property
    def pulse_hz(self) -> float:
        return visual_pulse_hz(self._beat)

    def set_color(self, color: QColor) -> None:
        _anim(self, QColor(self._color), QColor(color), 700,
              lambda v: (setattr(self, "_color", QColor(v)), self.update()))

    def set_glass(self, glass: bool) -> None:
        self._glass = glass; self.update()

    def set_beat(self, hz: float | None) -> None:
        self._beat = hz or self._beat
        self.setAccessibleDescription(
            f"Pulsing at {self.pulse_hz:.2f} per second, synced to a {self._beat:.1f} hertz beat")

    def set_playing(self, playing: bool) -> None:
        if playing == self._playing:
            return
        self._playing = playing
        self._frame.start()
        _anim(self, self._energy, 1.0 if playing else 0.0, 900 if playing else 1600,
              lambda v: setattr(self, "_energy", float(v)), QEasingCurve.InOutSine,
              on_done=self._maybe_idle)

    def _maybe_idle(self) -> None:
        if not self._playing or self.reduce_motion:
            self._frame.stop()
            self.update()

    def hideEvent(self, e) -> None:        # minimized / tray: zero paint cost
        self._frame.stop(); super().hideEvent(e)

    def showEvent(self, e) -> None:
        if self._playing and not self.reduce_motion:
            self._frame.start()
        super().showEvent(e)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        c = QPointF(w / 2, h / 2)
        base = min(w, h) * 0.2
        e = self._energy
        col = QColor(self._color)

        if self._playing and not self.reduce_motion:
            phase = ((time.monotonic() - self._t0) * self.pulse_hz) % 1.0
        else:
            phase = 0.25
        breath = 0.5 - 0.5 * math.cos(2 * math.pi * phase)
        r = base * (1.0 + 0.07 * breath * e)

        if not self._glass:  # high contrast: flat, outlined, no glow
            p.setPen(QPen(QColor("#FFFFFF"), 3)); p.setBrush(Qt.NoBrush)
            p.drawEllipse(c, r, r)
            p.setPen(QPen(QColor("#FFFF00"), 2))
            p.drawEllipse(c, r * (1 + 0.5 * breath * e), r * (1 + 0.5 * breath * e))
            p.end(); return

        # ambient glow
        reach = min(w, h) * 0.5            # glow must fade to 0 inside the widget (no hard edge)
        glow = QRadialGradient(c, reach)
        g0 = QColor(col); g0.setAlphaF(0.10 + 0.22 * e + 0.08 * breath * e)
        g1 = QColor(col); g1.setAlphaF(0.0)
        glow.setColorAt(0, g0); glow.setColorAt(0.45, QColor(col.red(), col.green(), col.blue(), int(30 * e) + 6))
        glow.setColorAt(1, g1)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(glow))
        p.drawEllipse(c, reach, reach)

        # ripples travelling outward, one per pulse
        if e > 0.01 and not self.reduce_motion:
            for k in range(3):
                q = (phase + k / 3.0) % 1.0
                rr = r * (1.05 + 1.25 * q)
                rc = QColor(col); rc.setAlphaF(0.32 * e * (1 - q) ** 2)
                p.setPen(QPen(rc, 1.4)); p.setBrush(Qt.NoBrush)
                p.drawEllipse(c, rr, rr)

        # orbit ring (static frame of reference)
        ring = QColor(255, 255, 255, 18)
        p.setPen(QPen(ring, 1)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, base * 1.9, base * 1.9)

        # core
        core = QRadialGradient(QPointF(c.x() - r * 0.35, c.y() - r * 0.4), r * 1.5)
        core.setColorAt(0.0, col.lighter(175))
        core.setColorAt(0.45, col)
        core.setColorAt(1.0, col.darker(330))
        dim = 0.55 + 0.45 * e
        p.setOpacity(dim)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(core))
        p.drawEllipse(c, r, r)

        # specular highlight (glass)
        spec = QRadialGradient(QPointF(c.x() - r * 0.35, c.y() - r * 0.45), r * 0.55)
        spec.setColorAt(0, QColor(255, 255, 255, 90)); spec.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(spec))
        p.drawEllipse(QPointF(c.x() - r * 0.3, c.y() - r * 0.38), r * 0.55, r * 0.42)
        p.setOpacity(1.0)
        p.end()


# ---------------------------------------------------------------------------
class AuroraBackground(QWidget):
    """Window backdrop: charcoal base, vignette and two soft blooms in the band colour."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Root")
        self._accent = QColor("#2DD4E8")
        self._palette = DARK

    def set_theme(self, palette: Palette, accent: QColor) -> None:
        self._palette = palette
        _anim(self, QColor(self._accent), QColor(accent), 900,
              lambda v: (setattr(self, "_accent", QColor(v)), self.update()))

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        r = self.rect()
        p.fillRect(r, QColor(self._palette.bg))
        if not self._palette.glass:
            p.end(); return
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        for cx, cy, rad, alpha, hue_shift in ((0.5, 0.48, 0.55, 0.16, 0), (0.12, 0.05, 0.45, 0.07, 25),
                                              (0.95, 1.0, 0.5, 0.06, -30)):
            col = QColor(self._accent)
            if hue_shift:
                hh, s, v, _ = col.getHsv()
                col.setHsv((hh + hue_shift) % 360, s, v)
            g = QRadialGradient(QPointF(r.width() * cx, r.height() * cy), max(r.width(), r.height()) * rad)
            c0 = QColor(col); c0.setAlphaF(alpha)
            c1 = QColor(col); c1.setAlphaF(0)
            g.setColorAt(0, c0); g.setColorAt(1, c1)
            p.setBrush(QBrush(g)); p.drawRect(r)
        v = QRadialGradient(QPointF(r.center()), max(r.width(), r.height()) * 0.75)
        v.setColorAt(0.6, QColor(0, 0, 0, 0)); v.setColorAt(1, QColor(self._palette.bg_deep))
        p.setBrush(QBrush(v)); p.drawRect(r)
        p.end()


# ---------------------------------------------------------------------------
class Toast(QFrame):
    """Subtle bottom-centre notification with optional action (e.g. Undo)."""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("Toast")
        self.setAccessibleName("Notification")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 10, 10); lay.setSpacing(12)
        self._dot = QLabel(); self._dot.setFixedSize(8, 8)
        self._label = QLabel()
        self._action = QPushButton(); self._action.setObjectName("ToastAction")
        self._action.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self._dot); lay.addWidget(self._label); lay.addWidget(self._action)
        self._fx = QGraphicsOpacityEffect(self); self._fx.setOpacity(0.0)
        self.setGraphicsEffect(self._fx)
        self._timer = QTimer(self); self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._callback: Callable | None = None
        self._action.clicked.connect(self._on_action)
        host.installEventFilter(self)
        self.hide()

    def show_message(self, text: str, accent: QColor, action: str | None = None,
                     callback: Callable | None = None, ms: int = 2800) -> None:
        self._label.setText(text)
        self._dot.setStyleSheet(f"background:{QColor(accent).name()}; border-radius:4px;")
        self._action.setVisible(bool(action)); self._action.setText(action or "")
        self._callback = callback
        self.setAccessibleDescription(text)
        self.adjustSize(); self._place(); self.show(); self.raise_()
        _anim(self, self._fx.opacity(), 1.0, 180, self._fx.setOpacity)
        self._timer.start(ms + (2500 if action else 0))
        _announce(self, text)

    def _on_action(self) -> None:
        cb, self._callback = self._callback, None
        self._fade_out()
        if cb:
            cb()

    def _fade_out(self) -> None:
        _anim(self, self._fx.opacity(), 0.0, 260, self._fx.setOpacity, on_done=self.hide)

    def _place(self) -> None:
        host = self.parentWidget()
        self.move((host.width() - self.width()) // 2, host.height() - self.height() - 28)

    def eventFilter(self, obj, ev) -> bool:
        if ev.type() == QEvent.Resize and self.isVisible():
            self._place()
        return False


def _announce(widget: QWidget, text: str) -> None:
    """Ask screen readers to speak `text` (Qt >= 6.8); silently no-op otherwise."""
    try:
        from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent
        QAccessible.updateAccessibility(QAccessibleAnnouncementEvent(widget, text))
    except Exception:
        pass


# ---------------------------------------------------------------------------
class Overlay(QWidget):
    """In-window modal: dims the app and centres a glass card. No OS pop-ups."""
    closed = Signal()

    def __init__(self, host: QWidget, dismissible: bool = True, width: int = 460) -> None:
        super().__init__(host)
        self.dismissible = dismissible
        self.card = QFrame(self); self.card.setObjectName("Card")
        self.card.setFixedWidth(width)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(32, 28, 32, 26); self.body.setSpacing(14)
        outer = QVBoxLayout(self); outer.addStretch(); 
        row = QHBoxLayout(); row.addStretch(); row.addWidget(self.card); row.addStretch()
        outer.addLayout(row); outer.addStretch()
        self._fx = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self._fx)
        host.installEventFilter(self)
        self.hide()

    def open(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self._fx.setOpacity(0.0); self.show(); self.raise_()
        _anim(self, 0.0, 1.0, 220, self._fx.setOpacity)

    def close_overlay(self) -> None:
        _anim(self, self._fx.opacity(), 0.0, 180, self._fx.setOpacity,
              on_done=lambda: (self.hide(), self.closed.emit()))

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key_Escape and self.dismissible:
            self.close_overlay()
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e) -> None:
        if self.dismissible and not self.card.geometry().contains(e.position().toPoint()):
            self.close_overlay()
        e.accept()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(4, 5, 7, 190))
        p.end()

    def eventFilter(self, obj, ev) -> bool:
        if ev.type() == QEvent.Resize and self.isVisible():
            self.setGeometry(self.parentWidget().rect())
        return False
