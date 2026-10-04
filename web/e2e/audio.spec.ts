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

test('speakers: speaker mode removes the beat-rate dropouts; headphones keep the true binaural beat', async ({ page }) => {
  await harness(page);
  const depth = (e: number[]) => 20 * Math.log10(Math.max(...e) / Math.max(Math.min(...e), 1e-6));
  for (const p of presets.filter((x) => x.channels.some((c) => c.kind === 'binaural'))) {
    // mono sum = what a phone speaker (or two speakers heard from afar) plays
    const spk = await page.evaluate((x) => (window as any).harness.analyze(x, 12, 0.5, true), p);
    expect(depth(spk.envM), p.name).toBeLessThan(8);         // was 11-20 dB dips before speaker mode
    const hp = await page.evaluate((x) => (window as any).harness.analyze(x, 12, 0.5, false), p);
    expect(depth(hp.envL), p.name).toBeLessThan(9);          // each ear is steady with headphones too
  }
  const r = await page.evaluate(() => (window as any).harness.renderPreset(
    { name: 't', band: 'ALPHA', channels: [{ kind: 'binaural', name: 'b', base_hz: 200, beat_hz: 10, volume: 0.5 }] }, 3, 0.85));
  expect(r.domL).toBeGreaterThan(199); expect(r.domL).toBeLessThan(201);   // headphones: still exact per ear
  expect(r.domR).toBeGreaterThan(209); expect(r.domR).toBeLessThan(211);
});

test('start fades in over 3 s and a pause can turn it around without a click', async ({ page }) => {
  await harness(page);
  const { env, jump } = await page.evaluate(() => (window as any).harness.renderDuck(3, 2, 1.2, 4));
  const full = 0.5 * 0.85 / Math.SQRT2;
  expect(env[0]).toBeLessThan(full * 0.01);                         // starts silent
  expect(env[50]).toBeLessThan(full * 0.12);                        // gentle start (x^2 curve)
  for (let i = 1; i <= 195; i++) expect(env[i]).toBeGreaterThanOrEqual(env[i - 1] * 0.98 - 1e-6);   // rising
  for (let i = 205; i <= 318; i++) expect(env[i]).toBeLessThanOrEqual(env[i - 1] * 1.02 + 1e-6);   // falling
  expect(Math.max(...env.slice(322))).toBeLessThan(full * 0.002);  // silent after the pause fade
  expect(jump).toBeLessThan(0.02);                                   // no clicks (200 Hz tone alone moves ~0.016/sample)
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

test('sleep timer ends playback on its own, with fade, and releases the device', async ({ page }) => {
  await harness(page);
  const r = await page.evaluate(() => (window as any).harness.runTimer(0.1, 0));   // 6 s timer, 3 s minimum fade
  expect(r.states).toContain('playing');
  expect(r.states.at(-1)).toBe('stopped');
  expect(r.elapsed).toBeGreaterThan(5.5);
  expect(r.elapsed).toBeLessThan(8);
  expect(r.ctxState).toBe('suspended');
});

test('pausing freezes the countdown; resuming continues it', async ({ page }) => {
  await harness(page);
  const r = await page.evaluate(() => (window as any).harness.pauseFreezesTimer());
  expect(r.a - r.b).toBeLessThan(0.15);      // paused 1.2 s: remaining barely moved
  expect(r.b - r.c).toBeGreaterThan(0.3);    // running again
  expect(r.state).toBe('fading');
});
