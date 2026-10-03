import { describe, expect, it } from 'vitest';
import { ceilingCurve } from './graph';
import { makeNoise } from './dsp';

describe('output ceiling', () => {
  it('is transparent below 0.7 and never exceeds 0.85', () => {
    const c = ceilingCurve();
    const at = (x: number) => c[Math.round(((x + 1) / 2) * (c.length - 1))]!;
    expect(at(0.5)).toBeCloseTo(0.5, 3);
    expect(at(-0.6)).toBeCloseTo(-0.6, 3);
    expect(Math.max(...c)).toBeLessThanOrEqual(0.85);
    expect(Math.min(...c)).toBeGreaterThanOrEqual(-0.85);
    for (let i = 1; i < c.length; i++) expect(c[i]!).toBeGreaterThanOrEqual(c[i - 1]!);   // monotonic
  });
});

describe('noise beds', () => {
  it('are peak-limited, loop-ready and spectrally tilted', () => {
    const sr = 8000;
    const [w] = makeNoise('white', sr * 2, sr / 4);
    const [b] = makeNoise('brown', sr * 2, sr / 4);
    expect(w!.length).toBe(sr * 2);
    const hf = (x: Float32Array) => { let d = 0; for (let i = 1; i < x.length; i++) d += (x[i]! - x[i - 1]!) ** 2; return d / x.length; };
    const pw = (x: Float32Array) => x.reduce((a, v) => a + v * v, 0) / x.length;
    expect(hf(b!) / pw(b!)).toBeLessThan(0.1 * (hf(w!) / pw(w!)));   // brown: far less HF than white
    expect(Math.max(...w!.map(Math.abs))).toBeLessThanOrEqual(0.71);
  });
});
