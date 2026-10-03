import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';

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
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1360, height: 860 } } },
    { name: 'phone', use: { ...devices['Pixel 7'] }, grep: /@phone/ },
  ],
  webServer: { command: `npx vite --port ${PORT} --strictPort`, port: PORT, reuseExistingServer: true },
});
