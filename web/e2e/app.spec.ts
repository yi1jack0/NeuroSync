// The three workflows from the product brief, plus safety, keyboard and sharing.
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const ACCEPTED = { masterVolume: 0.5, lastPreset: 'Alpha Focus', disclaimerAccepted: true, fadeMinutes: 5, highContrast: false, reduceMotion: false, sinkId: '', lang: 'en', theme: 'classic', langChosen: true, themeChosen: true };

async function open(page: Page, settings: object | null = ACCEPTED, path = '/') {
  await page.addInitScript((s) => { if (s && !sessionStorage.getItem('seeded')) { localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)); sessionStorage.setItem('seeded', '1'); } }, settings);
  await page.goto(path);
  await expect(page.getByRole('button', { name: /^(Play|Pause)$/ })).toBeVisible();
}
const setRange = (page: Page, name: string | RegExp, value: number) =>
  page.getByRole('slider', { name, exact: typeof name === 'string' }).first().evaluate((el, v) => {
    const i = el as HTMLInputElement; i.value = String(v); i.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);

test('first visit: Chinese + Liquid by default; safety notice must be acknowledged before any sound', async ({ page }) => {
  await page.goto('/');
  const dialog = page.getByRole('dialog', { name: '开始之前' });
  await expect(dialog).toBeVisible();
  expect(await page.evaluate(() => [document.documentElement.lang, document.documentElement.dataset.theme])).toEqual(['zh-Hans', 'pour']);
  await page.keyboard.press('Escape');                // cannot be dismissed
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: '我已了解，继续' }).click();
  await expect(dialog).toBeHidden();
  await page.reload();
  await expect(page.getByRole('dialog', { name: '开始之前' })).toBeHidden();   // remembered
});

test('returning visitors who never chose get the new defaults; explicit choices are kept', async ({ page }) => {
  // Saved by an older version: English + Classic were only the old defaults, never picked.
  await page.addInitScript(() => {
    if (sessionStorage.getItem('seeded')) return;                     // seed once, not on reload
    localStorage.setItem('neurosync.settings.v1', JSON.stringify({ disclaimerAccepted: true, lang: 'en', theme: 'classic' }));
    sessionStorage.setItem('seeded', '1');
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: '播放' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe('pour');
  await page.getByRole('button', { name: '菜单' }).click();
  await page.getByRole('radio', { name: 'English' }).click();
  await page.getByRole('radio', { name: 'Classic' }).click();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Play' })).toBeVisible();      // explicit choice kept
  expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe('classic');
});

test('workflow 1 — Quick Focus: pick a preset and play; volume is remembered', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: /^Alpha Focus,/ }).click();
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();
  await setRange(page, 'Master volume', 40);
  await page.getByRole('button', { name: 'Pause' }).click();
  await expect(page.getByText('Paused', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('slider', { name: 'Master volume' }).first()).toHaveValue('40');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Alpha Focus');
});

test('workflow 2 — Biohacker: custom generator, ambience, save as preset', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: 'New custom session' }).first().click();
  await setRange(page, 'Base', 200);
  await setRange(page, 'Beat', 10.5);
  await expect(page.getByText('10.5 Hz', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Add sound' }).click();
  await page.getByRole('button', { name: 'Gentle River' }).click();
  await page.getByRole('button', { name: 'Add sound' }).click();
  await page.getByRole('button', { name: 'Pink noise' }).click();
  await setRange(page, 'Pink Noise', 0.25);
  await page.getByRole('button', { name: 'Save as preset' }).click();
  await page.getByRole('textbox', { name: 'New preset name' }).fill('Deep Work Rain');
  await page.keyboard.press('Enter');
  await expect(page.getByText('Saved “Deep Work Rain” to My Presets')).toBeVisible();
  await page.reload();
  const saved = page.getByRole('button', { name: /^Deep Work Rain,/ });
  await expect(saved).toBeVisible();
  await saved.click();
  await expect(page.getByRole('slider', { name: 'Beat' })).toHaveValue('10.5');
  await expect(page.getByRole('group', { name: 'Pink Noise' })).toBeVisible();
});

test('built-in presets cannot be overwritten', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: 'Save as preset' }).click();
  await page.getByRole('textbox', { name: 'New preset name' }).fill('Delta Sleep');
  await page.keyboard.press('Enter');
  await expect(page.getByText(/can't be overwritten/)).toBeVisible();
});

test('workflow 3 — Sleep: Delta preset with a 45 min timer and 5 min fade', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: /^Delta Sleep,/ }).click();
  await page.getByRole('button', { name: 'Sleep timer' }).click();
  await page.getByRole('radio', { name: '45 minutes' }).click();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText(/Playing · 4[45]:\d\d remaining/)).toBeVisible();
  await page.getByRole('button', { name: 'Stop with fade-out' }).click();
  await expect(page.getByText('Fading out…')).toBeVisible();
  await expect(page.getByText('Session ended')).toBeVisible({ timeout: 6000 });   // >= 3 s fade
});

test('keyboard only: Space plays/pauses, M mutes, ? shows shortcuts', async ({ page }) => {
  await open(page);
  await page.locator('body').click({ position: { x: 640, y: 300 } });
  await page.keyboard.press('Space');
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();
  await page.keyboard.press('m');
  await expect(page.getByRole('button', { name: 'Mute', pressed: true }).first()).toBeVisible();
  await page.keyboard.press('Space');
  await expect(page.getByText('Paused', { exact: true })).toBeVisible();
  await page.keyboard.press('?');
  await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeHidden();
});

test('dragging the beat across a band boundary recolours the app', async ({ page }) => {
  await open(page);
  const accent = () => page.evaluate(() => document.documentElement.style.getPropertyValue('--accent'));
  expect(await accent()).toBe('#2DD4E8');            // alpha
  await setRange(page, 'Beat', 3);
  expect(await accent()).toBe('#7B61FF');            // delta
  await expect(page.getByText('DELTA · 0.5–4 Hz')).toBeVisible();
});

test('share link round trip', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await open(page);
  await page.getByRole('button', { name: /^Seaside Meditation,/ }).click();
  await page.getByRole('button', { name: 'Menu' }).click();
  await page.getByRole('button', { name: 'Share current preset (link)' }).click();
  await expect(page.getByText('Link copied to clipboard')).toBeVisible();
  const url = await page.evaluate(() => navigator.clipboard.readText());
  expect(url).toMatch(/#p=[A-Za-z0-9_-]+$/);
  await page.goto(url.replace(/^https?:\/\/[^/]+/, ''));
  await expect(page.getByText('Shared preset:')).toBeVisible();
  await page.getByRole('button', { name: 'Just play it' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Seaside Meditation');
});

test('accessibility: no serious axe violations (main view and open dialogs)', async ({ page }) => {
  await open(page);
  const main = await new AxeBuilder({ page }).analyze();
  const serious = main.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  expect(serious.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  await page.keyboard.press('?');
  const dlg = await new AxeBuilder({ page }).include('dialog[open]').analyze();
  expect(dlg.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([]);
});

test('@phone tabs switch between library, now playing and mixer', async ({ page }) => {
  await open(page);
  await page.getByRole('tab', { name: 'Library' }).click();
  await page.getByRole('button', { name: /^River Focus,/ }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('River Focus');   // loading returns to Now
  await page.getByRole('tab', { name: 'Mixer' }).click();
  await expect(page.getByRole('slider', { name: 'Gentle River' })).toBeVisible();
  const box = await page.getByRole('slider', { name: 'Gentle River' }).boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(36);                                    // thumb-sized target
});
