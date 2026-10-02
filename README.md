# NeuroSync Studio

*Tune your mind. Master your focus.*

Offline binaural-beat and ambient-sound studio for Windows. No telemetry, no accounts.

## Status

Milestone 1: domain model, audio engine, session/timer/fade, presets, WASAPI output, CLI.
Milestone 2: full PySide6 UI + UX (see [docs/DESIGN.md](docs/DESIGN.md)): glass dark theme,
band-driven accent, orb visualizer, glow sliders, tray, safety disclaimer, high contrast.
**Next:** bundled rain/café samples, installer, verification on real Windows hardware.

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
