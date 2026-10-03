import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';
import { S25_ULTRA } from './e2e/devices';

// In this repo's cloud sandbox Chromium is preinstalled; elsewhere `npx playwright install chromium`.
const local = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const executablePath = process.env.PW_CHROMIUM ?? (existsSync(local) ? local : undefined);
const PORT = 5199;

export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  fullyParallel: true,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    launchOptions: { executablePath, args: ['--autoplay-policy=no-user-gesture-required'] },
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1360, height: 860 } }, grepInvert: /@phone|@s25/, testIgnore: /prod\.spec\.ts/ },
    { name: 'phone', use: { ...devices['Pixel 7'] }, grep: /@phone/, testIgnore: /prod\.spec\.ts/ },
    // Samsung Galaxy S25 Ultra (Samsung Internet UA): all phone tests + S25-specific checks.
    { name: 's25-ultra', use: { ...S25_ULTRA }, grep: /@phone|@s25/, testIgnore: /prod\.spec\.ts/ },
    // Production build (service worker + CSP active), served by `vite preview`.
    { name: 'prod', testMatch: /prod\.spec\.ts/, use: { ...devices['Desktop Chrome'], baseURL: process.env.PROD_URL ?? 'http://localhost:4173', serviceWorkers: 'allow' } },
  ],
  webServer: [
    { command: `npx vite --port ${PORT} --strictPort`, port: PORT, reuseExistingServer: true },
    { command: 'npm run build && npx vite preview --port 4173 --strictPort', port: 4173, reuseExistingServer: true, timeout: 180_000 },
  ],
});
