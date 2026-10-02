"""Entry point. With no arguments, launches the desktop app.

    neurosync                       # NeuroSync Studio UI
    neurosync --list-presets
    neurosync --list-devices
    neurosync "Alpha Focus" --minutes 45 --fade 5 [--device N]
"""
from __future__ import annotations

import argparse
import time

from .app.presets import PresetRepository
from .app.session import Session, SessionState


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="neurosync")
    ap.add_argument("preset", nargs="?")
    ap.add_argument("--list-presets", action="store_true")
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--device", type=int)
    ap.add_argument("--exclusive", action="store_true", help="WASAPI exclusive mode")
    ap.add_argument("--minutes", type=float)
    ap.add_argument("--fade", type=float, default=0.0, help="fade-out minutes")
    ap.add_argument("--volume", type=float, default=0.5)
    args = ap.parse_args(argv)

    repo = PresetRepository()
    if args.list_presets:
        for p in repo.all():
            print(f"{p.category or p.band.label:<11} {p.name}  ({p.band.label})")
        return 0
    if args.list_devices:
        from .infra.audio_output import AudioOutputDeviceManager
        for d in AudioOutputDeviceManager().list_devices():
            print(f"{d.index:>3} {'*' if d.is_default else ' '} {d.name} [{d.hostapi}]")
        return 0
    if not args.preset:
        from .ui.app import main as run_ui
        return run_ui()

    preset = next((p for p in repo.all() if p.name.lower() == args.preset.lower()), None)
    if preset is None:
        ap.error(f"unknown preset: {args.preset!r}")

    print("HEADPHONES REQUIRED for binaural beats. Keep volume at a safe, comfortable level.")
    from .infra.audio_output import LowLatencyPlayer
    session = Session(preset, master_volume=args.volume)
    if args.minutes:
        session.set_timer(args.minutes, args.fade)
    session.play()
    player = LowLatencyPlayer(session.render, device=args.device, exclusive=args.exclusive)
    player.start()
    try:
        while session.state is not SessionState.STOPPED:
            time.sleep(0.25)
    except KeyboardInterrupt:
        session.stop()
        while session.state is not SessionState.STOPPED:
            time.sleep(0.1)
    finally:
        player.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
