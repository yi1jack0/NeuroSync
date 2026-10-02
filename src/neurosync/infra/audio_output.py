"""Hardware interface: device enumeration + low-latency WASAPI playback.

`sounddevice` is imported lazily so the rest of the app (and tests) run on
machines without PortAudio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..domain.limits import SAMPLE_RATE


@dataclass(frozen=True)
class OutputDevice:
    index: int
    name: str
    hostapi: str
    is_default: bool


def _sd():
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("audio output requires: pip install neurosync[audio]") from exc
    return sd


class AudioOutputDeviceManager:
    def list_devices(self, wasapi_only: bool = False) -> list[OutputDevice]:
        sd = _sd()
        apis = sd.query_hostapis()
        default_out = sd.default.device[1]
        devices = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] < 2:
                continue
            api = apis[d["hostapi"]]["name"]
            if wasapi_only and "WASAPI" not in api:
                continue
            devices.append(OutputDevice(i, d["name"], api, i == default_out))
        return devices


class LowLatencyPlayer:
    """Pulls blocks from `render(frames) -> (frames, 2) float32` via a PortAudio callback."""

    def __init__(self, render: Callable[[int], np.ndarray], device: int | None = None,
                 exclusive: bool = False, sample_rate: int = SAMPLE_RATE,
                 blocksize: int = 512) -> None:  # 512 @ 48 kHz ~ 10.7 ms per block
        self._render, self._device, self._exclusive = render, device, exclusive
        self._sr, self._blocksize = sample_rate, blocksize
        self._stream = None

    def start(self) -> None:
        sd = _sd()
        extra = None
        if self._device is not None and "WASAPI" in sd.query_hostapis(
                sd.query_devices(self._device)["hostapi"])["name"]:
            extra = sd.WasapiSettings(exclusive=self._exclusive)

        def callback(outdata, frames, time_info, status):
            outdata[:] = self._render(frames)

        self._stream = sd.OutputStream(samplerate=self._sr, blocksize=self._blocksize,
                                       device=self._device, channels=2, dtype="float32",
                                       latency="low", extra_settings=extra, callback=callback)
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class SimulatedPlayer:
    """Silent stand-in that drives `render` in real time (no audio hardware/PortAudio).

    Keeps timers, fades and the visualizer behaving exactly as with real output.
    """

    def __init__(self, render: Callable[[int], np.ndarray], sample_rate: int = SAMPLE_RATE,
                 blocksize: int = 2048) -> None:
        import threading
        self._render, self._sr, self._bs = render, sample_rate, blocksize
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        import time
        period = self._bs / self._sr
        next_t = time.monotonic()
        while not self._stop.is_set():
            self._render(self._bs)
            next_t += period
            self._stop.wait(max(0.0, next_t - time.monotonic()))

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
