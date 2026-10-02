"""Bundled ambience sounds (procedurally generated, CC0). Leaf package: stdlib only."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

ASSET_PREFIX = "asset:"


@dataclass(frozen=True)
class AmbienceSound:
    id: str
    name: str
    file: str
    category: str
    description: str
    loop_xfade_s: float = 2.0
    default_volume: float = 0.5
    duration_s: float = 0.0


@lru_cache(maxsize=1)
def catalog() -> tuple[AmbienceSound, ...]:
    raw = resources.files(__package__).joinpath("ambience", "catalog.json").read_text("utf-8")
    return tuple(AmbienceSound(**entry) for entry in json.loads(raw))


def get_sound(sound_id: str) -> AmbienceSound:
    for s in catalog():
        if s.id == sound_id:
            return s
    raise ValueError(f"unknown ambience sound: {sound_id!r}")


def read_asset_bytes(filename: str) -> bytes:
    return resources.files(__package__).joinpath("ambience", filename).read_bytes()
