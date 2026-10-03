// Audio graph verified in a real browser engine (OfflineAudioContext), not mocked.
import { expect, test, type Page } from '@playwright/test';
import presets from '../src/generated/presets.json' with { type: 'json' };

async function harness(page: Page) {
  await page.goto('/test/harness.html');
  await expect(page).toHaveTitle('harness ready');
}

const binaural = (base: number, beat: number, volume = 0.5) => ({
  name: 't', band: 'ALPHA', channels: [{ kind: 'binaural', name: 'b', base_hz: base, beat_hz: beat, volume }],
});

test('binaural: left ear = base, right ear = base + beat', async ({ page }) => {
  await harness(page);
  const r = await page.evaluate(() => (window as any).harness.renderPreset(
    { name: 't', band: 'ALPHA', channels: [{ kind: 'binaural', name: 'b', base_hz: 200, beat_hz: 10, volume: 0.5 }] }, 3, 0.85));
  expect(r.domL).toBeGreaterThan(199); expect(r.domL).toBeLessThan(201);
  expect(r.domR).toBeGreaterThan(209); expect(r.domR).toBeLessThan(211);
});

test('safety: out-of-range frequencies are clamped before reaching the oscillators', async ({ page }) => {
  await harness(page);
  const r = await page.evaluate((p) => (window as any).harness.renderPreset(p, 2, 0.85), binaural(5000, 99));
  expect(r.domL).toBeGreaterThan(995); expect(r.domL).toBeLessThan(1005);    // base clamped to 1000
  expect(r.domR).toBeGreaterThan(1035); expect(r.domR).toBeLessThan(1045);   // + beat clamped to 40
});

test('safety: master never exceeds 0.85 even with every fader at max', async ({ page }) => {
  await harness(page);
  const loud = {
    name: 'loud', band: 'BETA', channels: [
      { kind: 'binaural', name: 'b', base_hz: 200, beat_hz: 18, volume: 1 },
      { kind: 'noise', name: 'w', variant: 'white', volume: 1 },
      { kind: 'noise', name: 'p', variant: 'pink', volume: 1 },
      { kind: 'noise', name: 'r', variant: 'brown', volume: 1 },
      { kind: 'sample', name: 's', path: 'asset:river-gentle', volume: 1 }],
  };
  const r = await page.evaluate((p) => (window as any).harness.renderPreset(p, 3, 5), loud);  // master 5 requested
  expect(r.peak).toBeLessThanOrEqual(0.86);
});

test('every built-in preset renders sound (incl. bundled ambience)', async ({ page }) => {
  await harness(page);
  for (const p of presets) {
    const r = await page.evaluate((x) => (window as any).harness.renderPreset(x, 1.5, 0.5), p);
    expect(r.rmsL, p.name).toBeGreaterThan(0.005);
    expect(r.peak, p.name).toBeLessThanOrEqual(0.86);
  }
});

test('fade-out is logarithmic, monotonic and never shorter than 3 s', async ({ page }) => {
  await harness(page);
  const { end, env } = await page.evaluate(() => (window as any).harness.renderFade(0.5, 1, 6));
  expect(end).toBeCloseTo(4, 5);                                   // 0.5 s requested -> 3 s enforced
  const during = env.slice(102, 398);                              // 1.02 s .. 3.98 s
  for (let i = 1; i < during.length; i++) expect(during[i]).toBeLessThanOrEqual(during[i - 1] * 1.02 + 1e-6);
  const db = (v: number) => 20 * Math.log10(v / env[50]);
  expect(db(env[250])).toBeGreaterThan(-33); expect(db(env[250])).toBeLessThan(-27);   // midpoint ~ -30 dB
  expect(Math.max(...env.slice(402))).toBeLessThan(1e-4);         // silent after the end
});
