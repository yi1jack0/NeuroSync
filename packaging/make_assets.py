"""Generate packaging assets: app icon (.ico, multi-size PNG-in-ICO) and Windows version info.

    python packaging/make_assets.py      (needs PySide6; run headless with QT_QPA_PLATFORM=offscreen)
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication  # noqa: E402

from neurosync import __version__  # noqa: E402
from neurosync.ui.icons import pixmap  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(size: int) -> bytes:
    pm = pixmap("orb", QColor("#2DD4E8"), size, 1)
    ba = QByteArray(); buf = QBuffer(ba); buf.open(QIODevice.WriteOnly)
    pm.save(buf, "PNG")
    return bytes(ba)


def write_ico(path: Path) -> None:
    images = [(s, png_bytes(s)) for s in SIZES]
    out = bytearray(struct.pack("<HHH", 0, 1, len(images)))
    offset = 6 + 16 * len(images)
    for size, data in images:
        w = 0 if size >= 256 else size          # 0 means 256 in the ICO directory
        out += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for _, data in images:
        out += data
    path.write_bytes(bytes(out))


def write_version_info(path: Path) -> None:
    v = tuple(int(p) for p in (__version__.split(".") + ["0", "0", "0"])[:3]) + (0,)
    path.write_text(f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'NeuroSync'),
      StringStruct('FileDescription', 'NeuroSync Studio'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'NeuroSync'),
      StringStruct('LegalCopyright', 'Offline. No telemetry.'),
      StringStruct('OriginalFilename', 'NeuroSync.exe'),
      StringStruct('ProductName', 'NeuroSync Studio'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")


if __name__ == "__main__":
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    write_ico(HERE / "neurosync.ico")
    write_version_info(HERE / "version_info.txt")
    print("wrote neurosync.ico and version_info.txt for", __version__)
