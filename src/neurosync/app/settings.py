"""User preferences persisted as JSON next to the user's presets."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ..domain.limits import MASTER_GAIN_MAX, clamp
from .presets import default_user_dir


@dataclass
class Settings:
    master_volume: float = 0.5
    last_preset: str = "Alpha Focus"
    device_name: str = ""            # "" = system default
    exclusive_mode: bool = False
    disclaimer_accepted: bool = False
    fade_minutes: float = 5.0        # timers are per-session; only the fade length persists
    high_contrast: bool = False
    reduce_motion: bool = False
    close_to_tray: bool = True
    tray_hint_shown: bool = False

    def __post_init__(self) -> None:
        self.master_volume = clamp(self.master_volume, 0.0, MASTER_GAIN_MAX)

    @classmethod
    def load(cls, user_dir: Path | None = None) -> "Settings":
        path = settings_path(user_dir)
        try:
            data = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            return cls()
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})

    def save(self, user_dir: Path | None = None) -> None:
        path = settings_path(user_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def settings_path(user_dir: Path | None = None) -> Path:
    return (user_dir or default_user_dir()) / "settings.json"
