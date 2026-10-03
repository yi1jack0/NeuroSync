// Production build: offline after first visit, strict CSP with zero violations, installable.
import { expect, test } from '@playwright/test';

// PROD_URL lets the same suite run against `wrangler dev` (Cloudflare's runtime) or a live deploy.
const ORIGIN = new URL(process.env.PROD_URL ?? 'http://localhost:4173').origin;
const ACCEPTED = { masterVolume: 0.5, lastPreset: 'River Focus', disclaimerAccepted: true, fadeMinutes: 5, highContrast: false, reduceMotion: false, sinkId: '' };

test('works fully offline after the first visit (incl. bundled ambience)', async ({ page, context }) => {
  const violations: string[] = [];
  page.on('console', (m) => { if (/Content Security Policy|Refused to/.test(m.text())) violations.push(m.text()); });
  await context.addInitScript((s) => localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)), ACCEPTED);
  await page.goto('/');
  await expect(page.getByText('Offline ready')).toBeVisible({ timeout: 30_000 });
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('River Focus');
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();      // river ambience decoded from cache
  await page.getByRole('button', { name: /^Seaside Meditation,/ }).click();     // sea ambience, also cached
  await page.waitForTimeout(800);
  await expect(page.getByText(/couldn't|could not/i)).toHaveCount(0);
  expect(violations).toEqual([]);
});

test('strict CSP is active and the app makes no third-party requests', async ({ page, context }) => {
  const foreign: string[] = [];
  page.on('request', (r) => { if (!r.url().startsWith(ORIGIN) && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) foreign.push(r.url()); });
  await context.addInitScript((s) => localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)), ACCEPTED);
  await page.goto('/');
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("default-src 'self'");
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();
  expect(foreign).toEqual([]);
});

test('web app manifest is valid for installation', async ({ request }) => {
  const m = await (await request.get('/manifest.webmanifest')).json();
  expect(m.short_name).toBe('NeuroSync');
  expect(m.display).toBe('standalone');
  expect(m.icons.some((i: { sizes: string; purpose?: string }) => i.sizes === '512x512' && i.purpose === 'maskable')).toBe(true);
  for (const i of m.icons) expect((await request.get(i.src)).ok()).toBe(true);
});

test('privacy page is served and linked from the menu', async ({ page, context }) => {
  await context.addInitScript((s) => localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)), ACCEPTED);
  await page.goto('/');
  await page.getByRole('button', { name: 'Menu' }).click();
  await expect(page.getByRole('link', { name: /Privacy/ })).toHaveAttribute('href', '/privacy.html');
  await page.goto('/privacy.html');
  await expect(page.getByRole('heading', { name: 'Privacy' })).toBeVisible();
});
