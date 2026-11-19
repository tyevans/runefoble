import { defineConfig, devices } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';
import { APP_BASE_URL } from './e2e/support/environment';

/**
 * Runefoble Playwright BDD Configuration
 * Governed by ADR-0014 and Hard Invariant 7 (Blackbox Frontdoor TDD).
 *
 * The suite runs against the Kind stack through the Traefik ingress (TASK-0525). Start the stack first.
 * Global setup creates the personas in Zitadel. make test-e2e passes the admin token in the environment.
 */

const testDir = defineBddConfig({
  features: 'e2e/features/**/*.feature',
  steps: ['e2e/steps/**/*.ts', 'e2e/support/**/*.ts'],
});

export default defineConfig({
  testDir,
  fullyParallel: true,
  // The Zitadel hosted login takes several seconds per page in the Kind stack. A first sign-in can need over a minute.
  timeout: 180_000,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  globalSetup: './e2e/support/global_setup.ts',
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
    baseURL: APP_BASE_URL,
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
});
