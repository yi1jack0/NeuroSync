# NeuroSync Studio

*Tune your mind. Master your focus.*

Offline binaural-beat and ambient-sound studio for Windows. No telemetry, no accounts.

## Status

Milestone 1: domain model, audio engine, session/timer/fade, presets, WASAPI output, CLI.
Milestone 2: full PySide6 UI + UX (see [docs/DESIGN.md](docs/DESIGN.md)): glass dark theme,
band-driven accent, orb visualizer, glow sliders, tray, safety disclaimer, high contrast.
Milestone 3: bundled **Water** ambience (Gentle River, Deep River, Peaceful Sea Waves) +
4 presets that use them. **Next:** more ambience (rain, café), installer, verification on real Windows hardware.

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
