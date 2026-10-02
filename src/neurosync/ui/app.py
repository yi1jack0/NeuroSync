from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .icons import icon
from .main_window import MainWindow
from .theme import FONT_FAMILIES


def main(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("NeuroSync Studio")
    app.setOrganizationName("NeuroSync")
    app.setStyle("Fusion")                    # predictable base for the custom stylesheet
    app.setQuitOnLastWindowClosed(False)      # tray keeps the app alive
    font = QFont(); font.setFamilies(FONT_FAMILIES); font.setPointSizeF(10)
    app.setFont(font)
    app.setWindowIcon(icon("orb", "#2DD4E8", 64))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
