"""Business-rule constants (frequency safety, clipping, fades)."""

BASE_FREQ_MIN_HZ = 50.0
BASE_FREQ_MAX_HZ = 1000.0
BEAT_FREQ_MIN_HZ = 0.1
BEAT_FREQ_MAX_HZ = 40.0

MASTER_GAIN_MAX = 0.85
MIN_FADE_OUT_S = 3.0
FADE_FLOOR_DB = -60.0  # logarithmic fade runs 0 dB -> floor, then to silence

SAMPLE_RATE = 48_000


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
