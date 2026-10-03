// Phase 5: files, own sounds, undo, high contrast, phone audio route, accessibility everywhere.
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ACCEPTED = { masterVolume: 0.5, lastPreset: 'Alpha Focus', disclaimerAccepted: true, fadeMinutes: 5, highContrast: false, reduceMotion: false, sinkId: '' };
async function open(page: Page, extra: object = {}) {
  await page.addInitScript((s) => { if (!sessionStorage.getItem('seeded')) { localStorage.setItem('neurosync.settings.v1', JSON.stringify(s)); sessionStorage.setItem('seeded', '1'); } }, { ...ACCEPTED, ...extra });
  await page.goto('/');
  await expect(page.getByRole('button', { name: /^(Play|Pause|播放|暂停)$/ })).toBeVisible();
}
const seriousAxe = async (page: Page) => (await new AxeBuilder({ page }).analyze()).violations
  .filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => `${v.id} (${v.nodes.length})`);

test('export a preset file and import it back (desktop-compatible JSON)', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: /^Ocean Night,/ }).click();
  await page.getByRole('button', { name: 'Menu' }).click();
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export preset file' }).click()]);
  const path = join(mkdtempSync(join(tmpdir(), 'ns-')), 'p.json');
  await download.saveAs(path);
  const json = JSON.parse(readFileSync(path, 'utf8'));
  expect(json.name).toBe('Ocean Night');
  expect(json.channels.map((c: { path: string }) => c.path)).toContain('asset:sea-calm');   // same format as desktop
  json.name = 'Ocean Night Copy';
  writeFileSync(path, JSON.stringify(json));
  await page.getByRole('button', { name: 'Menu' }).click();
  const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.getByRole('button', { name: 'Import preset file' }).click()]);
  await chooser.setFiles(path);
  await expect(page.getByText('Imported “Ocean Night Copy”')).toBeVisible();
  await expect(page.getByRole('button', { name: /^Ocean Night Copy,/ })).toBeVisible();
});

test('import rejects invalid files', async ({ page }) => {
  await open(page);
  const path = join(mkdtempSync(join(tmpdir(), 'ns-')), 'bad.json');
  writeFileSync(path, '{"name": "x", "band": "NOPE"}');
  await page.getByRole('button', { name: 'Menu' }).click();
  const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.getByRole('button', { name: 'Import preset file' }).click()]);
  await chooser.setFiles(path);
  await expect(page.getByText("That file isn't a valid NeuroSync preset")).toBeVisible();
});

test('your own sound file: stored on the device, playable, survives reload', async ({ page }) => {
  const dir = mkdtempSync(join(tmpdir(), 'ns-'));
  const wav = join(dir, 'my_rain.wav');
  execFileSync('ffmpeg', ['-loglevel', 'error', '-f', 'lavfi', '-i', 'anoisesrc=d=4:c=pink:a=0.3', '-ac', '2', '-ar', '48000', wav]);
  await open(page);
  await page.getByRole('button', { name: 'Add sound' }).click();
  const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.getByRole('button', { name: 'Your own sound file…' }).click()]);
  await chooser.setFiles(wav);
  await expect(page.getByText('Added my_rain')).toBeVisible();
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Save as preset' }).click();
  await page.getByRole('textbox', { name: 'New preset name' }).fill('My Rain Focus');
  await page.keyboard.press('Enter');
  await expect(page.getByText('Saved “My Rain Focus” to My Presets')).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: /^My Rain Focus,/ }).click();
  await expect(page.getByRole('slider', { name: 'my_rain', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();
  await expect(page.getByText(/no longer stored|couldn't/i)).toHaveCount(0);
});

test('deleting a preset can be undone', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: 'Save as preset' }).click();
  await page.getByRole('textbox', { name: 'New preset name' }).fill('Temp');
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Actions for Temp' }).click();
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByRole('button', { name: /^Temp,/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Undo' }).click();
  await expect(page.getByRole('button', { name: /^Temp,/ })).toBeVisible();
});

test('high contrast: yellow accent, flat visuals, still no serious axe violations', async ({ page }) => {
  await open(page, { highContrast: true });
  expect(await page.evaluate(() => document.documentElement.classList.contains('hc'))).toBe(true);
  expect(await page.evaluate(() => document.documentElement.style.getPropertyValue('--accent'))).toBe('#FFFF00');
  expect(await seriousAxe(page)).toEqual([]);
});

test('reduced motion: the orb stops animating', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await open(page);
  await page.getByRole('button', { name: 'Play' }).click();
  await page.waitForTimeout(1500);
  const frame = () => page.locator('canvas').evaluate((c: HTMLCanvasElement) => c.toDataURL().length + ':' + c.toDataURL().slice(-200));
  const a = await frame(); await page.waitForTimeout(700); const b = await frame();
  expect(a).toBe(b);
});

test('@phone audio plays through the lock-screen-safe media element route', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(page.getByText('Playing', { exact: true })).toBeVisible();
  const mode = await page.evaluate(() => (window as unknown as { __ns?: { mode: string } }).__ns?.mode);
  expect(mode).toBe('element');
  expect(await page.evaluate(() => navigator.mediaSession?.playbackState)).toBe('playing');
});

test('@phone no serious axe violations on every tab', async ({ page }) => {
  await open(page);
  for (const tab of ['Now', 'Mixer', 'Library']) {
    await page.getByRole('tab', { name: tab }).click();
    expect(await seriousAxe(page), tab).toEqual([]);
  }
});

test('clicking the orb cycles its speed (Calm -> Lively -> Slow), remembered across reloads', async ({ page }) => {
  await open(page);
  const orb = page.getByRole('button', { name: /^Visualizer speed/ });
  await expect(orb).toHaveAccessibleName(/Calm/);
  await orb.click();
  await expect(page.getByText('Orb speed: Lively')).toBeVisible();
  await orb.click();
  await expect(page.getByText('Orb speed: Slow')).toBeVisible();
  await expect(orb).toHaveAccessibleName(/Slow/);
  await page.reload();
  await expect(page.getByRole('button', { name: /^Visualizer speed: Slow/ })).toBeVisible();
  await page.getByRole('button', { name: /^Visualizer speed/ }).focus();
  await page.keyboard.press('Enter');                               // keyboard works too
  await expect(page.getByText('Orb speed: Calm')).toBeVisible();
});

test.describe('Chinese (Simplified)', () => {
  test.use({ locale: 'zh-CN' });

  test('a Chinese browser gets Chinese automatically, including the safety notice', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('dialog', { name: '开始之前' })).toBeVisible();
    await expect(page.getByText('请使用立体声耳机。')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.lang)).toBe('zh-Hans');
    await page.getByRole('button', { name: '我已了解，继续' }).click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('α 波专注');
    await expect(page.getByRole('button', { name: '播放' })).toBeVisible();
  });

  test('switch to English and back from the menu; choice is remembered', async ({ page }) => {
    await open(page, { lang: 'zh' });
    await page.getByRole('button', { name: '菜单' }).click();
    await page.getByRole('radio', { name: 'English' }).click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Alpha Focus');
    expect(await page.evaluate(() => document.documentElement.lang)).toBe('en');
    await page.reload();
    await expect(page.getByRole('button', { name: 'Play' })).toBeVisible();
    await page.getByRole('button', { name: 'Menu' }).click();
    await page.getByRole('radio', { name: '简体中文' }).click();
    await expect(page.getByText('语言：简体中文')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('α 波专注');
  });

  test('works fully in Chinese: library, mixer, timer shortcut, save, ambience names', async ({ page }) => {
    await open(page, { lang: 'zh' });
    await page.getByRole('button', { name: /^海边冥想，/ }).click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('海边冥想');
    await expect(page.getByText('θ 波 · 4–8 Hz')).toBeVisible();
    await expect(page.getByRole('slider', { name: '宁静海浪', exact: true })).toBeVisible();
    await page.locator('body').click({ position: { x: 5, y: 400 } });
    await page.keyboard.press('t');
    await expect(page.getByRole('radio', { name: '45 分钟' })).toBeVisible();      // T shortcut works in Chinese
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: '保存为预设' }).click();
    await page.getByRole('textbox', { name: '新预设名称' }).fill('我的海边');
    await page.keyboard.press('Enter');
    await expect(page.getByText('已将“我的海边”保存到我的预设')).toBeVisible();
    await expect(page.getByRole('group', { name: '我的预设' })).toBeVisible();
    await page.getByRole('button', { name: '播放' }).click();
    await expect(page.getByText('正在播放', { exact: true })).toBeVisible();
  });
});
