"""Serializable domain entities: channel configs and presets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bands import BrainwaveBand
from .limits import (BASE_FREQ_MAX_HZ, BASE_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ,
                     BEAT_FREQ_MIN_HZ, clamp)

BINAURAL, NOISE, SAMPLE = "binaural", "noise", "sample"
NOISE_VARIANTS = ("white", "pink", "brown")


@dataclass
class ChannelConfig:
    """Configuration of one MixerChannel (what a Preset stores)."""
    kind: str                      # binaural | noise | sample
    name: str
    volume: float = 0.5            # 0.0 .. 1.0
    pan: float = 0.0               # -1.0 .. 1.0
    muted: bool = False
    base_hz: float = 200.0         # binaural only
    beat_hz: float = 10.0          # binaural only
    variant: str = "pink"          # noise only
    path: str = ""                 # sample only

    def __post_init__(self) -> None:
        if self.kind not in (BINAURAL, NOISE, SAMPLE):
            raise ValueError(f"unknown channel kind: {self.kind!r}")
        if self.kind == NOISE and self.variant not in NOISE_VARIANTS:
            raise ValueError(f"unknown noise variant: {self.variant!r}")
        self.volume = clamp(self.volume, 0.0, 1.0)
        self.pan = clamp(self.pan, -1.0, 1.0)
        self.base_hz = clamp(self.base_hz, BASE_FREQ_MIN_HZ, BASE_FREQ_MAX_HZ)
        self.beat_hz = clamp(self.beat_hz, BEAT_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChannelConfig":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class Preset:
    name: str
    band: BrainwaveBand
    channels: list[ChannelConfig] = field(default_factory=list)
    icon: str = "waves"
    description: str = ""
    category: str = ""             # sidebar group; defaults to band label

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "band": self.band.name, "icon": self.icon,
                "description": self.description, "category": self.category,
                "channels": [c.to_dict() for c in self.channels]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Preset":
        return cls(name=data["name"], band=BrainwaveBand[data["band"]],
                   channels=[ChannelConfig.from_dict(c) for c in data.get("channels", [])],
                   icon=data.get("icon", "waves"),
                   description=data.get("description", ""),
                   category=data.get("category", ""))
