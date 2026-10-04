// Samsung Galaxy S25 Ultra specifics: every orientation/mode fits, landscape layout,
// Android back gesture, haptics, touch target sizes.
import { expect, test, type Page } from '@playwright/test';
import { S25_ULTRA, S25_ULTRA_APP, S25_ULTRA_LANDSCAPE, S25_ULTRA_LANDSCAPE_APP } from './devices';

const ACCEPTED = { masterVolume: 0.5, lastPreset: 'River Focus', disclaimerAccepted: true, fadeMinutes: 5, highContrast: false, reduceMotion: false, sinkId: '', lang: 'en', theme: 'classic', langChosen: true, themeChosen: true };
async function open(page: Page) {
  await page.addInitScript((s) => {
    if (!sessionStorage.getItem('seeded')) { localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)); sessionStorage.setItem('seeded', '1'); }
    (window as unknown as { __vib: number[] }).__vib = [];
    Object.defineProperty(navigator, 'vibrate', { value: (ms: number) => { (window as unknown as { __vib: number[] }).__vib.push(ms); return true; } });
  }, ACCEPTED);
  await page.goto('/');
  await expect(page.getByRole('button', { name: /^(Play|Pause)$/ })).toBeVisible();
}
const noOverflow = (page: Page) => page.evaluate(() => [document.documentElement.scrollWidth - innerWidth, document.documentElement.scrollHeight - innerHeight]);

for (const [label, dev] of [['browser portrait', S25_ULTRA], ['installed portrait', S25_ULTRA_APP],
  ['browser landscape', S25_ULTRA_LANDSCAPE], ['installed landscape', S25_ULTRA_LANDSCAPE_APP]] as const) {
  test.describe(`@s25 ${label}`, () => {
    test.use({ viewport: dev.viewport, deviceScaleFactor: dev.deviceScaleFactor });
    test('fits the screen on every tab, nothing overflows', async ({ page }) => {
      await open(page);
      for (const tab of ['Library', 'Mixer', 'Now']) {
        await page.getByRole('tab', { name: tab }).click();
        expect(await noOverflow(page), tab).toEqual([0, 0]);
      }
      await page.getByRole('button', { name: 'Play' }).click();
      await expect(page.getByText('Playing', { exact: true })).toBeVisible();
      const orb = await page.getByRole('button', { name: /^Visualizer speed/ }).boundingBox();
      expect(orb!.height).toBeGreaterThan(140);                         // the orb stays a real feature
    });
  });
}

test.describe('@s25 landscape layout', () => {
  test.use({ viewport: S25_ULTRA_LANDSCAPE.viewport });
  test('tabs become a side rail and the orb sits beside the info', async ({ page }) => {
    await open(page);
    const tabs = await page.getByRole('tablist').boundingBox();
    expect(tabs!.width).toBeLessThan(100);
    expect(tabs!.height).toBeGreaterThan(tabs!.width);
    const title = await page.getByRole('heading', { level: 1 }).boundingBox();
    const orb = await page.getByRole('button', { name: /^Visualizer speed/ }).boundingBox();
    expect(orb!.x).toBeGreaterThan(title!.x + title!.width / 2);
  });
});

test('@s25 Android back gesture closes tabs and dialogs before leaving the app', async ({ page }) => {
  await open(page);
  await page.getByRole('tab', { name: 'Mixer' }).click();
  await expect(page.getByRole('slider', { name: 'Gentle River' })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole('tab', { name: 'Now' })).toHaveAttribute('aria-selected', 'true');
  expect(page.url()).toMatch(/localhost:\d+\/$/);                        // still in the app
  await page.getByRole('button', { name: 'Menu' }).click();
  await page.getByRole('button', { name: 'Keyboard shortcuts' }).click();
  await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeHidden();
  // Closing in the UI must not leave a stale history entry behind:
  await page.getByRole('tab', { name: 'Library' }).click();
  await page.getByRole('tab', { name: 'Now' }).click();
  await expect(page.getByRole('tab', { name: 'Now' })).toHaveAttribute('aria-selected', 'true');
});

test('@s25 haptic tick when the beat crosses a brainwave band, and on orb speed change', async ({ page }) => {
  await open(page);
  await page.getByRole('tab', { name: 'Mixer' }).click();
  const beat = page.getByRole('slider', { name: 'Beat' });
  await beat.evaluate((el) => { const i = el as HTMLInputElement; i.value = '12'; i.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(await page.evaluate(() => (window as unknown as { __vib: number[] }).__vib.length)).toBe(0);   // 10 -> 12 Hz: still alpha
  await beat.evaluate((el) => { const i = el as HTMLInputElement; i.value = '16'; i.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(await page.evaluate(() => (window as unknown as { __vib: number[] }).__vib)).toEqual([12]);   // alpha -> beta
  await page.getByRole('tab', { name: 'Now' }).click();
  await page.getByRole('button', { name: /^Visualizer speed/ }).click();
  expect(await page.evaluate(() => (window as unknown as { __vib: number[] }).__vib.length)).toBe(2);
});

test('@s25 touch targets are at least 44 px', async ({ page }) => {
  await open(page);
  for (const name of ['Sleep timer', 'Menu']) {
    const b = await page.getByRole('button', { name, exact: true }).boundingBox();
    expect(b!.width, name).toBeGreaterThanOrEqual(44);
    expect(b!.height, name).toBeGreaterThanOrEqual(44);
  }
  for (const tab of ['Library', 'Now', 'Mixer']) {
    const b = await page.getByRole('tab', { name: tab }).boundingBox();
    expect(b!.height, tab).toBeGreaterThanOrEqual(44);
  }
});

test.describe('@s25 earphones reminder', () => {
  test.use({ viewport: S25_ULTRA.viewport, hasTouch: true, isMobile: true });
  test('phones start in speaker mode with an earphones reminder; Headphones hides it', async ({ page }) => {
    await open(page);
    const reminder = page.getByText('Put on earphones for the real binaural beat');
    await expect(page.getByRole('radio', { name: 'Speaker' })).toHaveAttribute('aria-checked', 'true');
    await expect(reminder).toBeVisible();
    await page.getByRole('button', { name: 'Play' }).click();
    await expect(page.getByText(/binaural beats need earphones/)).toBeVisible();   // one-time tip on play
    expect(await noOverflow(page)).toEqual([0, 0]);
    await page.getByRole('radio', { name: 'Headphones' }).click();
    await expect(reminder).toBeHidden();
    await page.reload();                                                          // choice remembered
    await expect(page.getByRole('radio', { name: 'Headphones' })).toHaveAttribute('aria-checked', 'true');
  });
});
