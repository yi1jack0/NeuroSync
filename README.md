# NeuroSync Studio

*Tune your mind. Master your focus.*

Offline binaural-beat and ambient-sound studio for Windows. No telemetry, no accounts.

## Status

Milestone 1: domain model, audio engine, session/timer/fade, presets, WASAPI output, CLI.
Milestone 2: full PySide6 UI + UX (see [docs/DESIGN.md](docs/DESIGN.md)): glass dark theme,
band-driven accent, orb visualizer, glow sliders, tray, safety disclaimer, high contrast.
Milestone 3: bundled **Water** ambience (Gentle River, Deep River, Peaceful Sea Waves) +
4 presets that use them. Milestone 4: Windows installer (PyInstaller + Inno Setup, built in CI).
Milestone 5: **web version** (`web/`, Svelte 5 + Web Audio, offline PWA) for **neurosync.ejai.ai**:
see [web/README.md](web/README.md) and the go-live steps in [docs/WEB_LAUNCH.md](docs/WEB_LAUNCH.md).
**Next:** real-device checks (docs/WEB_LAUNCH.md §4), more ambience (rain, café).

## Languages

The **desktop app is English only** (product decision). The **web app** supports English and Simplified Chinese (简体中文): see `web/README.md`.

## Layout

```
src/neurosync/
  domain/   bands, limits (safety rules), serializable models (Preset, ChannelConfig)
  engine/   OscillatorSource, SampleSource/noise, MixerEngine, LogFade   (pure NumPy)
  app/      Session (state/timer/fade), AudioGraphBuilder, PresetRepository, builtin presets
  infra/    AudioOutputDeviceManager, LowLatencyPlayer (sounddevice / WASAPI)
  ui/       PySide6 interface: theme, widgets, panels, overlays, main window
```

## Develop

```
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[audio,ui,dev]"
pytest
neurosync                      # launch the app
neurosync --list-presets
neurosync "Alpha Focus" --minutes 45 --fade 5
```

## Enforced rules

Base 50–1000 Hz · beat 0.1–40 Hz · master gain ≤ 0.85 (plus hard clip guard) ·
logarithmic fade-out ≥ 3 s on stop and timer expiry.

## Bundled ambience

`src/neurosync/assets/ambience/` holds looping `.ogg` beds (~1.5 MB total), listed in `catalog.json`.
They are **procedurally generated** (CC0, no third-party samples) by `tools/ambience/gen_*.py`:

```
pip install -e ".[assets]"                      # scipy + matplotlib, build-time only
python tools/ambience/analyze.py sea-calm       # quality gates + spectrogram PNG
python tools/ambience/build.py                  # re-render all -> assets/ambience/
```

Presets reference them portably as `"path": "asset:sea-calm"`. Loops are equal-power cross-faded
at load time (click-free) and kept as int16 in RAM, shared between channels.

## Windows installer

```
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```
Freezes the app with PyInstaller (`packaging/neurosync.spec`, onedir), runs the packaged app's
`--selftest` (bundled sounds, presets, codecs, PortAudio, Qt), then builds
`dist-installer\NeuroSync-Setup-<version>.exe` with Inno Setup 6 (`packaging/installer.iss`):
per-user install (no admin prompt), Start-menu shortcut, optional desktop shortcut, clean
uninstall that asks before deleting your presets (`%APPDATA%\NeuroSync`).

CI (`.github/workflows/windows-installer.yml`, run it from the Actions tab or push a `v*` tag)
builds on a Windows runner, silently installs the result, self-tests the *installed* app and
uninstalls, then uploads the installer and a portable zip as artifacts.

The installer is **unsigned**, so Windows SmartScreen will warn on first run
("More info -> Run anyway") until you buy a code-signing certificate.
