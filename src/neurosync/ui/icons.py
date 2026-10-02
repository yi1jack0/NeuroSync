"""Vector icons painted with QPainter: crisp at any DPI, tinted to the theme."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)


def icon(name: str, color: QColor | str = "#E9ECF1", size: int = 20) -> QIcon:
    ic = QIcon()
    for scale in (1, 2):
        ic.addPixmap(pixmap(name, color, size, scale))
    return ic


def pixmap(name: str, color: QColor | str, size: int, scale: int = 1) -> QPixmap:
    pm = QPixmap(size * scale, size * scale)
    pm.setDevicePixelRatio(scale)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)           # all glyphs drawn on a 24-unit grid
    c = QColor(color)
    pen = QPen(c, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    _GLYPHS[name](p, c)
    p.end()
    return pm


def _play(p, c):
    path = QPainterPath(QPointF(8, 5.5))
    path.lineTo(18.5, 12); path.lineTo(8, 18.5); path.closeSubpath()
    p.setBrush(c); p.drawPath(path)


def _pause(p, c):
    p.setBrush(c); p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(7, 5.5, 3.6, 13), 1.2, 1.2)
    p.drawRoundedRect(QRectF(13.4, 5.5, 3.6, 13), 1.2, 1.2)


def _stop(p, c):
    p.setBrush(c); p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(7, 7, 10, 10), 2, 2)


def _timer(p, c):
    p.drawEllipse(QPointF(12, 13), 7.5, 7.5)
    p.drawLine(QPointF(12, 13), QPointF(12, 9))
    p.drawLine(QPointF(12, 13), QPointF(14.5, 14.5))
    p.drawLine(QPointF(10, 3.5), QPointF(14, 3.5))


def _more(p, c):
    p.setBrush(c); p.setPen(Qt.NoPen)
    for x in (6, 12, 18):
        p.drawEllipse(QPointF(x, 12), 1.7, 1.7)


def _plus(p, c):
    p.drawLine(QPointF(12, 6), QPointF(12, 18)); p.drawLine(QPointF(6, 12), QPointF(18, 12))


def _close(p, c):
    p.drawLine(QPointF(7, 7), QPointF(17, 17)); p.drawLine(QPointF(17, 7), QPointF(7, 17))


def _speaker(p, c):
    path = QPainterPath(QPointF(4, 9.5))
    path.lineTo(7.5, 9.5); path.lineTo(12, 5.5); path.lineTo(12, 18.5)
    path.lineTo(7.5, 14.5); path.lineTo(4, 14.5); path.closeSubpath()
    p.drawPath(path)


def _volume(p, c):
    _speaker(p, c)
    p.drawArc(QRectF(11, 8, 6, 8), -60 * 16, 120 * 16)
    p.drawArc(QRectF(11, 5, 10, 14), -60 * 16, 120 * 16)


def _mute(p, c):
    _speaker(p, c)
    p.drawLine(QPointF(15, 9.5), QPointF(20, 14.5)); p.drawLine(QPointF(20, 9.5), QPointF(15, 14.5))


def _headphones(p, c):
    p.drawArc(QRectF(4, 4, 16, 16), 0, 180 * 16)
    p.setBrush(c)
    p.drawRoundedRect(QRectF(3.5, 12, 4, 7), 1.5, 1.5)
    p.drawRoundedRect(QRectF(16.5, 12, 4, 7), 1.5, 1.5)


def _save(p, c):
    path = QPainterPath(QPointF(6, 4))
    path.lineTo(18, 4); path.lineTo(18, 20); path.lineTo(12, 15.5); path.lineTo(6, 20)
    path.closeSubpath()
    p.drawPath(path)


def _speaker_out(p, c):  # output device
    p.drawRoundedRect(QRectF(6, 3.5, 12, 17), 2.5, 2.5)
    p.drawEllipse(QPointF(12, 14), 3, 3)
    p.setBrush(c); p.drawEllipse(QPointF(12, 7.5), 0.9, 0.9)


def _minimize(p, c):  # minimize to tray
    p.drawRoundedRect(QRectF(4, 4, 16, 16), 3, 3)
    p.drawLine(QPointF(8, 15), QPointF(16, 15))


def _wave(p, c):
    path = QPainterPath(QPointF(3, 12))
    for i in range(1, 37):
        x = 3 + i * 0.5
        path.lineTo(x, 12 - 5 * math.sin((x - 3) / 18 * 2 * math.pi * 1.5))
    p.drawPath(path)


def _noise(p, c):
    hs = [4, 9, 6, 12, 7, 10, 5, 8]
    for i, h in enumerate(hs):
        x = 4.5 + i * 2.1
        p.drawLine(QPointF(x, 12 - h / 2), QPointF(x, 12 + h / 2))


def _file(p, c):
    path = QPainterPath(QPointF(6, 3.5))
    path.lineTo(14, 3.5); path.lineTo(18.5, 8); path.lineTo(18.5, 20.5); path.lineTo(6, 20.5)
    path.closeSubpath()
    p.drawPath(path)
    p.drawPolyline([QPointF(14, 3.5), QPointF(14, 8), QPointF(18.5, 8)])


def _keyboard(p, c):
    p.drawRoundedRect(QRectF(3, 6.5, 18, 11), 2, 2)
    p.setBrush(c); p.setPen(Qt.NoPen)
    for x in (6.5, 10, 13.5, 17):
        p.drawEllipse(QPointF(x, 10), 0.9, 0.9)
    p.drawRoundedRect(QRectF(8, 13, 8, 1.6), 0.8, 0.8)


def _orb(p, c):
    g = QRadialGradient(QPointF(10, 9), 11)
    g.setColorAt(0, QColor(c).lighter(160))
    g.setColorAt(0.6, c)
    g.setColorAt(1, QColor(c).darker(250))
    p.setPen(Qt.NoPen); p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(12, 12), 9.5, 9.5)


_GLYPHS = {"play": _play, "pause": _pause, "stop": _stop, "timer": _timer, "more": _more,
           "plus": _plus, "close": _close, "volume": _volume, "mute": _mute,
           "headphones": _headphones, "save": _save, "device": _speaker_out,
           "minimize": _minimize, "wave": _wave, "noise": _noise, "file": _file,
           "keyboard": _keyboard, "orb": _orb}
