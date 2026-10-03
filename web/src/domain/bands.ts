export type BandName = 'DELTA' | 'THETA' | 'ALPHA' | 'BETA' | 'GAMMA';

export interface Band { name: BandName; label: string; low: number; high: number; color: string; category: string }

export const BANDS: readonly Band[] = [
  { name: 'DELTA', label: 'Delta', low: 0.5, high: 4, color: '#7B61FF', category: 'Sleep' },
  { name: 'THETA', label: 'Theta', low: 4, high: 8, color: '#B18CFF', category: 'Meditate' },
  { name: 'ALPHA', label: 'Alpha', low: 8, high: 14, color: '#2DD4E8', category: 'Focus' },
  { name: 'BETA', label: 'Beta', low: 14, high: 30, color: '#3EE0A1', category: 'Focus' },
  { name: 'GAMMA', label: 'Gamma', low: 30, high: 100, color: '#F7B955', category: 'Creativity' },
];

export const CATEGORY_ORDER = ['Sleep', 'Meditate', 'Focus', 'Creativity'];

export function band(name: BandName): Band {
  return BANDS.find((b) => b.name === name) ?? BANDS[2]!;
}

export function bandForFrequency(hz: number): Band {
  for (const b of BANDS) if (hz >= b.low && hz < b.high) return b;
  return hz < BANDS[0]!.low ? BANDS[0]! : BANDS[BANDS.length - 1]!;
}

/** Fold the beat down by octaves to a calm visual rate (never a flicker: photosensitivity). */
export function visualPulseHz(beatHz: number, ceiling = 1.25): number {
  let hz = Math.max(beatHz, 0.05);
  while (hz > ceiling) hz /= 2;
  return hz;
}
