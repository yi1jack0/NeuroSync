// Screenshots of the real app (dev server must be running): node scripts/screens.mjs [baseURL]
import { chromium } from '@playwright/test';
import { existsSync, mkdirSync } from 'node:fs';
const base = process.argv[2] ?? 'http://localhost:5199';
const out = process.env.OUT ?? '../docs/screenshots';
mkdirSync(out, { recursive: true });
const local = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser = await chromium.launch({ executablePath: existsSync(local) ? local : undefined, args: ['--autoplay-policy=no-user-gesture-required'] });
const accepted = { masterVolume: 0.5, lastPreset: 'River Focus', disclaimerAccepted: true, fadeMinutes: 5, highContrast: false, reduceMotion: false, sinkId: '' };
async function shot(name, { width, height, dpr = 1, mobile = false, settings = accepted, act } ) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: dpr, isMobile: mobile, hasTouch: mobile });
  await ctx.addInitScript((s) => { if (s) localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)); }, settings);
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.error('PAGEERROR', name, e.message));
  page.on('console', (m) => m.type() === 'error' && console.error('CONSOLE', name, m.text()));
  await page.goto(base);
  await page.waitForTimeout(600);
  if (act) await act(page);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${out}/${name}.png` });
  await ctx.close();
  console.log('saved', name);
}
const play = async (p) => { await p.getByRole('button', { name: 'Play' }).click(); await p.waitForTimeout(1500); };
await shot('webapp-desktop', { width: 1440, height: 900, act: play });
await shot('webapp-first-visit', { width: 1440, height: 900, settings: null });
await shot('webapp-tablet', { width: 834, height: 1112, act: async (p) => { await play(p); await p.getByRole('button', { name: 'Expand mixer' }).click(); } });
await shot('webapp-phone-now', { width: 390, height: 844, dpr: 2, mobile: true, act: play });
await shot('webapp-phone-mixer', { width: 390, height: 844, dpr: 2, mobile: true, act: async (p) => { await p.getByRole('tab', { name: 'Mixer' }).click(); } });
await shot('webapp-phone-library', { width: 390, height: 844, dpr: 2, mobile: true, act: async (p) => { await p.getByRole('tab', { name: 'Library' }).click(); } });
await shot('webapp-high-contrast', { width: 1440, height: 900, settings: { ...accepted, highContrast: true, lastPreset: 'Gamma Creativity' }, act: play });
await browser.close();
