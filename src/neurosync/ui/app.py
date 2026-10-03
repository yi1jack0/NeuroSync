from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .. import __version__
from .icons import icon
from .main_window import MainWindow
from .theme import FONT_FAMILIES

APP_USER_MODEL_ID = "NeuroSync.Studio"


def _set_windows_app_id() -> None:
    """Own taskbar identity so the pinned icon / grouping isn't python.exe's."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass


def selftest(out: str | None) -> int:
    """Packaging smoke test: proves bundled data, codecs and Qt work in this build.

    Used by CI on the frozen executable: NeuroSync.exe --selftest result.txt
    """
    lines: list[str] = []
    ok = True
    try:
        from ..app.builder import AudioGraphBuilder
        from ..app.presets import PresetRepository
        from ..assets import catalog
        from ..engine.sources import SampleSource

        sounds = catalog()
        assert len(sounds) >= 3, f"catalog has {len(sounds)} sounds"
        for s in sounds:
            SampleSource.from_asset(s.id).read(512)
        lines.append(f"ambience assets decoded: {len(sounds)}")

        tmp = Path(tempfile.mkdtemp())
        repo = PresetRepository(tmp)
        presets = repo.builtin()
        assert len(presets) >= 5, f"only {len(presets)} built-in presets"
        for p in presets:
            AudioGraphBuilder().build(p).render(1024)
        lines.append(f"built-in presets rendered: {len(presets)}")

        from ..app.settings import Settings
        win = MainWindow(repo=repo, settings=Settings(disclaimer_accepted=True),
                         settings_dir=tmp, player_factory=lambda *a: None, devices=[])
        QApplication.processEvents()
        win.grab()
        lines.append("main window rendered")
        win._release_player()
        try:
            import sounddevice  # noqa: F401
            lines.append("sounddevice (PortAudio) importable")
        except Exception as exc:
            if sys.platform == "win32":      # the Windows wheel bundles PortAudio: must work
                ok = False
                lines.append(f"FAIL sounddevice: {exc}")
            else:                            # Linux/macOS use a system PortAudio
                lines.append(f"note: sounddevice unavailable here ({exc})")
    except Exception:
        ok = False
        lines.append("FAIL\n" + traceback.format_exc())
    text = f"NeuroSync {__version__} selftest: {'OK' if ok else 'FAILED'}\n" + "\n".join(lines) + "\n"
    if out:
        Path(out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv)
    _set_windows_app_id()
    app = QApplication.instance() or QApplication(args)
    app.setApplicationName("NeuroSync Studio")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("NeuroSync")
    app.setStyle("Fusion")                    # predictable base for the custom stylesheet
    app.setQuitOnLastWindowClosed(False)      # tray keeps the app alive
    font = QFont(); font.setFamilies(FONT_FAMILIES); font.setPointSizeF(10)
    app.setFont(font)
    app.setWindowIcon(icon("orb", "#2DD4E8", 64))
    if "--selftest" in args:
        i = args.index("--selftest")
        return selftest(args[i + 1] if i + 1 < len(args) else None)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
