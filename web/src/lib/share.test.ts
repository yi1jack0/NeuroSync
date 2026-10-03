import { describe, expect, it } from 'vitest';
import { decodePreset, encodePreset, presetTokenFromHash } from './share';
import { parsePreset } from '../domain/preset';

const p = parsePreset({
  name: 'Deep Work Rain', band: 'ALPHA', channels: [
    { kind: 'binaural', name: 'Binaural', base_hz: 200, beat_hz: 10.5, volume: 0.4 },
    { kind: 'sample', name: 'River', path: 'asset:river-gentle', volume: 0.42 },
    { kind: 'sample', name: 'Mine', path: 'local:abc', volume: 0.3 }],
});

describe('share links', () => {
  it('round-trips a preset, dropping device-only sounds', async () => {
    const token = await encodePreset(p);
    expect(token).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(token.length).toBeLessThan(400);
    const back = await decodePreset(token);
    expect(back.name).toBe('Deep Work Rain');
    expect(back.channels.map((c) => c.path)).toEqual(['', 'asset:river-gentle']);
  });
  it('rejects garbage and clamps hostile values', async () => {
    await expect(decodePreset('not-a-preset')).rejects.toThrow();
    const evil = await encodePreset({ ...p, channels: [{ ...p.channels[0]!, base_hz: 99999, volume: 50 }] });
    const back = await decodePreset(evil);
    expect(back.channels[0]!.base_hz).toBe(1000);
    expect(back.channels[0]!.volume).toBe(1);
  });
  it('parses only well-formed fragments', () => {
    expect(presetTokenFromHash('#p=abc_-1')).toBe('abc_-1');
    expect(presetTokenFromHash('#x=abc')).toBeNull();
    expect(presetTokenFromHash('#p=<script>')).toBeNull();
  });
});
