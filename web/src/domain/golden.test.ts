// The web port must reproduce the desktop engine's numbers (tools/export_golden.py).
import { describe, expect, it } from 'vitest';
import golden from './golden.json';
import { bandForFrequency } from './bands';
import * as L from './limits';
import { parseChannel, parsePreset } from './preset';
import { logFadeGain, makeLoopable } from '../audio/dsp';
import presets from '../generated/presets.json';

describe('golden values from the Python engine', () => {
  it('limits match', () => {
    const g = golden.limits;
    expect([L.BASE_FREQ_MIN_HZ, L.BASE_FREQ_MAX_HZ, L.BEAT_FREQ_MIN_HZ, L.BEAT_FREQ_MAX_HZ, L.MASTER_GAIN_MAX, L.MIN_FADE_OUT_S, L.FADE_FLOOR_DB])
      .toEqual([g.base_min, g.base_max, g.beat_min, g.beat_max, g.master_max, g.min_fade_s, g.fade_floor_db]);
  });

  it('channel clamping', () => {
    for (const c of golden.clamp) {
      const [base_hz, beat_hz, volume, pan] = c.in;
      const ch = parseChannel({ kind: 'binaural', name: 'x', base_hz, beat_hz, volume, pan });
      expect([ch.base_hz, ch.beat_hz, ch.volume, ch.pan]).toEqual(c.out);
    }
  });

  it('band lookup', () => {
    for (const b of golden.bands) expect(bandForFrequency(b.hz).name).toBe(b.band);
  });

  it('logarithmic fade curve', () => {
    for (const p of golden.fade.points) expect(logFadeGain(p.t)).toBeCloseTo(p.gain, 5);
  });

  it('loop crossfade', () => {
    const input = golden.loopable.input.map((ch) => Float32Array.from(ch));
    const out = makeLoopable(input, golden.loopable.xfade);
    out.forEach((ch, c) => ch.forEach((v, i) => expect(v).toBeCloseTo(golden.loopable.output[c]![i]!, 5)));
  });

  it('master slider mapping', () => {
    for (const m of golden.master_slider) expect(L.sliderToGain(m.slider)).toBeCloseTo(m.gain, 9);
  });

  it('built-in presets parse identically to desktop', () => {
    expect(presets.map(parsePreset)).toEqual(golden.presets);
  });
});
