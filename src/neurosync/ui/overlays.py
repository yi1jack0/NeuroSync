"""In-window overlay cards: first-launch safety notice and keyboard shortcuts."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QWidget

from .icons import pixmap
from .widgets import Overlay

SAFETY_POINTS = [
    ("Use stereo headphones.",
     "Binaural beats only exist when each ear hears its own tone — speakers mix them."),
    ("Start quiet.", "Begin at a low volume and raise it slowly to a comfortable level."),
    ("Never while driving", "or doing anything that needs your full attention."),
    ("Check with a doctor first", "if you have epilepsy, a seizure disorder, a heart condition, "
     "or are pregnant."),
]


class DisclaimerOverlay(Overlay):
    """Mandatory on first launch: cannot be dismissed except by acknowledging."""
    accepted = Signal()

    def __init__(self, host: QWidget, accent: QColor) -> None:
        super().__init__(host, dismissible=False, width=500)
        self.setAccessibleName("Safety information")
        head = QHBoxLayout(); head.setSpacing(14)
        ic = QLabel(); ic.setPixmap(pixmap("headphones", accent, 40, 2)); head.addWidget(ic)
        tl = QLabel("Before you begin"); tl.setStyleSheet("font-size: 17pt; font-weight: 300;")
        head.addWidget(tl); head.addStretch()
        self.body.addLayout(head)
        for title, text in SAFETY_POINTS:
            lbl = QLabel(f"<b>{title}</b> <span style='color:#9AA3AF'>{text}</span>")
            lbl.setWordWrap(True); lbl.setTextFormat(Qt.RichText)
            self.body.addWidget(lbl)
        note = QLabel("NeuroSync is a relaxation and focus tool, not a medical device.")
        note.setObjectName("Faint"); note.setWordWrap(True)
        self.body.addSpacing(4); self.body.addWidget(note)
        row = QHBoxLayout(); row.addStretch()
        self.ok = QPushButton("I understand — continue"); self.ok.setObjectName("Primary")
        self.ok.setCursor(Qt.PointingHandCursor); self.ok.setDefault(True)
        row.addWidget(self.ok)
        self.body.addSpacing(6); self.body.addLayout(row)
        self.ok.clicked.connect(self._accept)

    def open(self) -> None:
        super().open(); self.ok.setFocus()

    def _accept(self) -> None:
        self.accepted.emit(); self.close_overlay()


SHORTCUTS = [
    ("Space", "Play / pause"), ("Ctrl+Space", "Stop with fade-out"),
    ("Ctrl+↑ / Ctrl+↓", "Master volume"), ("M", "Mute master"),
    ("Ctrl+T", "Sleep timer"), ("Ctrl+S", "Save as preset"), ("Ctrl+N", "New custom session"),
    ("F6", "Move between library, transport and mixer"),
    ("↑ ↓ ← →  PgUp PgDn", "Adjust focused slider"), ("Enter", "Load highlighted preset"),
    ("Ctrl+M", "Minimize to tray"), ("Ctrl+Shift+H", "High contrast"),
    ("F1", "This help"), ("Ctrl+Q", "Quit (with fade-out)"),
]


class ShortcutsOverlay(Overlay):
    def __init__(self, host: QWidget) -> None:
        super().__init__(host, dismissible=True, width=480)
        self.setAccessibleName("Keyboard shortcuts")
        t = QLabel("Keyboard shortcuts"); t.setStyleSheet("font-size: 15pt; font-weight: 300;")
        self.body.addWidget(t)
        grid = QGridLayout(); grid.setHorizontalSpacing(18); grid.setVerticalSpacing(8)
        for r, (keys, what) in enumerate(SHORTCUTS):
            k = QLabel(keys); k.setObjectName("Kbd"); k.setAlignment(Qt.AlignCenter)
            d = QLabel(what); d.setObjectName("Dim")
            grid.addWidget(k, r, 0, Qt.AlignLeft); grid.addWidget(d, r, 1)
        self.body.addLayout(grid)
        row = QHBoxLayout(); row.addStretch()
        self.ok = QPushButton("Done"); row.addWidget(self.ok)
        self.body.addLayout(row)
        self.ok.clicked.connect(self.close_overlay)

    def open(self) -> None:
        super().open(); self.ok.setFocus()
