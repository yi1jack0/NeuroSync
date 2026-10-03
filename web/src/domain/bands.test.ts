import { describe, expect, it } from 'vitest';
import { ORB_SPEEDS, visualPulseHz } from './bands';

describe('orb speeds (photosensitivity)', () => {
  it('never exceed 1.25 Hz for any beat, at any speed, and stay octave-locked to the beat', () => {
    for (const s of ORB_SPEEDS) {
      expect(s.ceiling).toBeLessThanOrEqual(1.25);
      for (const beat of [0.1, 0.5, 2, 6, 10, 10.5, 18, 30, 40]) {
        const hz = visualPulseHz(beat, s.ceiling);
        expect(hz).toBeLessThanOrEqual(1.25);
        expect(Math.log2(beat / hz) % 1).toBeCloseTo(0, 9);   // beat / 2^k
      }
    }
  });
  it('are ordered slow -> calm -> lively', () => {
    expect(ORB_SPEEDS.map((s) => s.name)).toEqual(['Slow', 'Calm', 'Lively']);
    expect(visualPulseHz(10, ORB_SPEEDS[0].ceiling)).toBeLessThan(visualPulseHz(10, ORB_SPEEDS[2].ceiling));
  });
});
