import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: '*.spec.ts', timeout: 60000,
  fullyParallel: false, workers: 1,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173', actionTimeout: 10000, trace: 'retain-on-failure'},
  projects: [
    {name: 'desktop', use: {...devices['Desktop Chrome']}},
    {name: 'mobile', use: {...devices['Pixel 7']}},
  ],
});
