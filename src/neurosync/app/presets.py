from __future__ import annotations

import json
import os
import re
from importlib import resources
from pathlib import Path

from ..domain.models import Preset


def default_user_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "NeuroSync"


class PresetRepository:
    """Built-in presets (read-only, packaged) + user presets as one JSON file each."""

    def __init__(self, user_dir: Path | None = None) -> None:
        self.user_dir = (user_dir or default_user_dir()) / "presets"

    def builtin(self) -> list[Preset]:
        out = []
        for entry in sorted(resources.files("neurosync.app").joinpath("builtin").iterdir(),
                            key=lambda e: e.name):
            if entry.name.endswith(".json"):
                out.extend(Preset.from_dict(d) for d in json.loads(entry.read_text("utf-8")))
        return out

    def user(self) -> list[Preset]:
        if not self.user_dir.exists():
            return []
        return [Preset.from_dict(json.loads(p.read_text("utf-8")))
                for p in sorted(self.user_dir.glob("*.json"))]

    def all(self) -> list[Preset]:
        return self.builtin() + self.user()

    def save(self, preset: Preset) -> Path:
        self.user_dir.mkdir(parents=True, exist_ok=True)
        path = self.user_dir / f"{_slug(preset.name)}.json"
        path.write_text(json.dumps(preset.to_dict(), indent=2), encoding="utf-8")
        return path

    def export(self, preset: Preset, dest: Path) -> None:  # "share" = hand over the file
        dest.write_text(json.dumps(preset.to_dict(), indent=2), encoding="utf-8")

    def import_file(self, src: Path) -> Preset:
        preset = Preset.from_dict(json.loads(src.read_text("utf-8")))
        self.save(preset)
        return preset

    def delete(self, name: str) -> None:
        (self.user_dir / f"{_slug(name)}.json").unlink(missing_ok=True)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "preset"
