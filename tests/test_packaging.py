import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import struct
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from neurosync.ui.app import selftest  # noqa: E402

PKG = Path(__file__).resolve().parents[1] / "packaging"


def test_selftest_passes_and_reports(tmp_path, qapp=None):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    out = tmp_path / "r.txt"
    assert selftest(str(out)) == 0
    text = out.read_text(encoding="utf-8")
    assert "selftest: OK" in text and "ambience assets decoded: 3" in text


def test_icon_is_valid_multi_size_ico():
    import subprocess, sys
    subprocess.run([sys.executable, str(PKG / "make_assets.py")], check=True,
                   env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    data = (PKG / "neurosync.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1) and count == 7
    for i in range(count):
        w, h, _, _, planes, bpp, size, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
        assert data[offset:offset + 8] == b"\x89PNG\r\n\x1a\n" and offset + size <= len(data)


def test_installer_and_spec_present_and_consistent():
    iss = (PKG / "installer.iss").read_text()
    assert "PrivilegesRequired=lowest" in iss and "..\\dist\\NeuroSync" in iss
    spec = (PKG / "neurosync.spec").read_text()
    assert "collect_data_files(\"neurosync\")" in spec and "sounddevice" in spec
