from __future__ import annotations

from ..domain.models import BINAURAL, NOISE, SAMPLE, ChannelConfig, Preset
from ..engine.mixer import MixerChannel, MixerEngine
from ..engine.sources import AudioSource, OscillatorSource, SampleSource, noise_source


class AudioGraphBuilder:
    """Translates a Preset into a concrete mixer graph."""

    def build(self, preset: Preset, master_volume: float = 0.5) -> MixerEngine:
        mixer = MixerEngine()
        mixer.master_volume = master_volume
        for cfg in preset.channels:
            mixer.channels.append(self.build_channel(cfg))
        return mixer

    def build_channel(self, cfg: ChannelConfig) -> MixerChannel:
        source: AudioSource
        if cfg.kind == BINAURAL:
            source = OscillatorSource(cfg.base_hz, cfg.beat_hz)
        elif cfg.kind == NOISE:
            source = noise_source(cfg.variant)
        else:
            source = SampleSource.from_file(cfg.path)
        return MixerChannel(cfg.name, source, cfg.volume, cfg.pan, cfg.muted,
                            is_binaural=cfg.kind == BINAURAL)
