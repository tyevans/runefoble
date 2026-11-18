/**
 * Caravan Board Playwright BDD Step Definitions
 *
 * Drives <runefoble-caravan-board> through its UI. The only fault injection is a
 * 503 response at the network boundary, used to prove the error path (ADR-0015).
 * Governed by ADR-0014 and Hard Invariant 7. TASK-0677.
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

const CARD = 'runefoble-caravan-contract-card';

Given('the caravan board is open', async ({ page }) => {
  await page.goto('#/caravans');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('runefoble-caravan-board', { timeout: 15_000 });
});

Given('the caravan route {string} responds with status {int}', async ({ page }, action: string, status: number) => {
  await page.route(`**/caravans/contracts/*/${action}`, (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Caravan route service is unavailable.' }),
    })
  );
});

Given('an accepted caravan contract {string} is on the board', async ({}, _contractTitle: string) => {
  throw new Error(
    'Caravan contract setup through public shared-world routes is not implemented. ' +
      'Blocked until the App Shell mounts the board (TASK-0677 follow-up).'
  );
});

Given('a caravan contract {string} is in transit on the board', async ({}, _contractTitle: string) => {
  throw new Error(
    'Caravan contract setup through public shared-world routes is not implemented. ' +
      'Blocked until the App Shell mounts the board (TASK-0677 follow-up).'
  );
});

Then('I should see the caravan notice {string}', async ({ page }, message: string) => {
  await expect(page.locator('runefoble-caravan-board .notification-banner').filter({ hasText: message })).toBeVisible();
});

Then('the contract card should show status {string}', async ({ page }, status: string) => {
  await expect(page.locator(`${CARD} .status-badge`).filter({ hasText: status })).toBeVisible();
});

Then('the contract card should not show {string}', async ({ page }, text: string) => {
  await expect(page.locator(`${CARD} .status-badge`).filter({ hasText: text })).toHaveCount(0);
});
