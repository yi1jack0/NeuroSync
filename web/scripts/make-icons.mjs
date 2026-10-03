// Renders the PWA/touch icons from the orb design (dev-time; outputs are committed).
import { chromium } from '@playwright/test';
import { existsSync } from 'node:fs';

const local = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser = await chromium.launch({ executablePath: existsSync(local) ? local : undefined });
const page = await browser.newPage();
const html = (size, pad, bg) => `<body style="margin:0;background:${bg}">
  <svg width="${size}" height="${size}" viewBox="0 0 100 100"><defs><radialGradient id="g" cx=".36" cy=".32" r=".75">
  <stop offset="0" stop-color="#E0FCFF"/><stop offset=".45" stop-color="#2DD4E8"/><stop offset="1" stop-color="#06303A"/></radialGradient>
  <radialGradient id="h" cx=".5" cy=".5" r=".5"><stop offset=".55" stop-color="#2DD4E8" stop-opacity=".25"/><stop offset="1" stop-color="#2DD4E8" stop-opacity="0"/></radialGradient></defs>
  ${bg === 'transparent' ? '' : `<rect width="100" height="100" fill="${bg}"/><circle cx="50" cy="50" r="${50 - pad / 2}" fill="url(#h)"/>`}
  <circle cx="50" cy="50" r="${(100 - 2 * pad) / 2 * 0.8}" fill="url(#g)"/></svg></body>`;
for (const [name, size, pad, bg] of [['icon-192.png', 192, 8, '#121417'], ['icon-512.png', 512, 8, '#121417'],
  ['maskable-512.png', 512, 22, '#121417'], ['apple-touch-icon.png', 180, 10, '#121417']]) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(html(size, pad, bg));
  await page.screenshot({ path: `public/icons/${name}`, omitBackground: bg === 'transparent' });
  console.log('wrote', name);
}
await browser.close();
