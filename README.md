# NeuroSync Studio

*Tune your mind. Master your focus.*

Offline binaural-beat and ambient-sound studio for Windows. No telemetry, no accounts.

## Status

Milestone 1 (this commit): domain model, audio engine, session/timer/fade, preset
repository, WASAPI output, headless CLI. **Next:** PySide6 UI (sidebar / orb visualizer /
mixer / top bar), system tray, first-launch headphone disclaimer, bundled rain/café samples.

## Layout

```
src/neurosync/
  domain/   bands, limits (safety rules), serializable models (Preset, ChannelConfig)
  engine/   OscillatorSource, SampleSource/noise, MixerEngine, LogFade   (pure NumPy)
  app/      Session (state/timer/fade), AudioGraphBuilder, PresetRepository, builtin presets
  infra/    AudioOutputDeviceManager, LowLatencyPlayer (sounddevice / WASAPI)
  ui/       (placeholder)
```

## Develop

```
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[audio,dev]"
pytest
neurosync --list-presets
neurosync "Alpha Focus" --minutes 45 --fade 5
```

## Enforced rules

Base 50–1000 Hz · beat 0.1–40 Hz · master gain ≤ 0.85 (plus hard clip guard) ·
logarithmic fade-out ≥ 3 s on stop and timer expiry.
