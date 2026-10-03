// Business rules. Mirrors src/neurosync/domain/limits.py (verified by golden.test.ts).
export const BASE_FREQ_MIN_HZ = 50;
export const BASE_FREQ_MAX_HZ = 1000;
export const BEAT_FREQ_MIN_HZ = 0.1;
export const BEAT_FREQ_MAX_HZ = 40;
export const MASTER_GAIN_MAX = 0.85;
export const MIN_FADE_OUT_S = 3;
export const FADE_FLOOR_DB = -60;

export const clamp = (v: number, lo: number, hi: number): number =>
  Number.isFinite(v) ? Math.max(lo, Math.min(hi, v)) : lo;

/** Master slider shows 0-100 % of the *safe* range: 100 % == 0.85 gain. */
export const sliderToGain = (pct: number): number => (clamp(pct, 0, 100) / 100) * MASTER_GAIN_MAX;
export const gainToSlider = (g: number): number => Math.round((clamp(g, 0, MASTER_GAIN_MAX) / MASTER_GAIN_MAX) * 100);
