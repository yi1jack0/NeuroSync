# One-shot local Windows build:  powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
# Requires: Python 3.10+ on PATH, Inno Setup 6 (https://jrsoftware.org/isdl.php) for the installer step.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m venv .venv-build
.\.venv-build\Scripts\python -m pip install --upgrade pip
.\.venv-build\Scripts\pip install -e ".[audio,build]"

$env:QT_QPA_PLATFORM = "offscreen"
.\.venv-build\Scripts\python packaging\make_assets.py
.\.venv-build\Scripts\pyinstaller packaging\neurosync.spec --noconfirm --clean

# Prove the frozen app can find its data, codecs, PortAudio and Qt.
$result = Join-Path $env:TEMP "neurosync-selftest.txt"
Remove-Item $result -ErrorAction SilentlyContinue
$p = Start-Process dist\NeuroSync\NeuroSync.exe -ArgumentList "--selftest", $result -Wait -PassThru
Get-Content $result
if ($p.ExitCode -ne 0) { throw "Packaged app self-test failed" }

$version = (& .\.venv-build\Scripts\python -c "import neurosync; print(neurosync.__version__)").Trim()
$iscc = @("$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { Write-Warning "Inno Setup not found - skipping installer. Portable build is in dist\NeuroSync."; exit 0 }
& $iscc "/DAppVersion=$version" packaging\installer.iss
Write-Host "Installer: dist-installer\NeuroSync-Setup-$version.exe"
