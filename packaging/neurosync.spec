# PyInstaller spec. Build:  pyinstaller packaging/neurosync.spec --noconfirm
# onedir (not onefile): starts instantly and triggers far fewer antivirus false positives.
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent
IS_WIN = sys.platform == "win32"

datas = collect_data_files("neurosync")                 # assets/ambience/*, app/builtin/*.json
datas += collect_data_files("sounddevice")              # PortAudio DLL bundled by the wheel
datas += collect_data_files("soundfile")                # libsndfile
binaries = collect_dynamic_libs("sounddevice") + collect_dynamic_libs("soundfile")

# The app only needs QtCore/Gui/Widgets. Dropping the rest saves ~100 MB.
UNUSED_QT = ["QtNetwork", "QtQml", "QtQuick", "QtQuickWidgets", "QtQuick3D", "QtWebEngineCore",
             "QtWebEngineWidgets", "QtWebChannel", "QtMultimedia", "QtMultimediaWidgets", "Qt3DCore",
             "QtSql", "QtTest", "QtSvg", "QtPdf", "QtCharts", "QtDataVisualization", "QtBluetooth",
             "QtPositioning", "QtSensors", "QtSerialPort", "QtDesigner", "QtHelp", "QtOpenGL",
             "QtOpenGLWidgets", "QtDBus", "QtXml", "QtConcurrent", "QtPrintSupport"]
excludes = [f"PySide6.{m}" for m in UNUSED_QT] + [
    "scipy", "matplotlib", "tkinter", "pytest", "PIL", "pandas", "IPython"]  # build-time only / unused

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    datas=datas, binaries=binaries,
    hiddenimports=["sounddevice", "soundfile", "_sounddevice_data", "_soundfile_data"],
    excludes=excludes, noarchive=False,
)
# Python-level excludes don't stop PyInstaller copying Qt's shared libraries/plugins; drop them.
DROP = ("Qt6Quick", "Qt6Qml", "Qt6Pdf", "Qt6Network", "Qt6VirtualKeyboard", "Qt6OpenGL", "Qt6Svg",
        "qmltooling", "networkinformation", "/tls/", "qtvirtualkeyboard", "libQt6Quick", "libQt6Qml",
        "libQt6Pdf", "libQt6Network", "libQt6Svg", "libQt6OpenGL", "libQt6VirtualKeyboard")
def _keep(entry):
    name = (entry[0] + " " + str(entry[1])).replace("\\", "/")
    return not any(tok in name for tok in DROP)
a.binaries = [e for e in a.binaries if _keep(e)]
a.datas = [e for e in a.datas if _keep(e)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="NeuroSync", console=False, debug=False, strip=False, upx=False,
    icon=str(ROOT / "packaging" / "neurosync.ico") if IS_WIN else None,
    version=str(ROOT / "packaging" / "version_info.txt") if IS_WIN else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="NeuroSync", strip=False, upx=False)
