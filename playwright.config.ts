import { defineConfig, devices } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';

/**
 * Runefoble Playwright BDD Configuration
 * Governed by ADR-0014 and Hard Invariant 7 (Blackbox Frontdoor TDD).
 */

const testDir = defineBddConfig({
  features: 'e2e/features/**/*.feature',
  steps: ['e2e/steps/**/*.ts', 'e2e/support/**/*.ts'],
});

export default defineConfig({
  testDir,
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [
        ['github'],
        ['html', { open: 'never' }],
      ]
    : [
        ['html', { open: 'never' }],
        ['list'],
      ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: [
    {
      command: 'uv run python gateway/api/src/gateway_api/main.py',
      url: 'http://localhost:8000/healthz',
      reuseExistingServer: true,
      timeout: 60_000,
      env: {
        SPICEDB_ENDPOINT: process.env.SPICEDB_ENDPOINT || 'mock',
        RUNEFOBLE_SPICEDB_ENDPOINT: process.env.RUNEFOBLE_SPICEDB_ENDPOINT || 'mock',
        AUTH_DEV_MODE: 'true',
        RUNEFOBLE_AUTH_DEV_MODE: 'true',
      },
    },
    {
      command: 'cd frontend && pnpm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
