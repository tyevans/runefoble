/**
 * App Shell Route and API State Step Definitions (TASK-0642).
 * Governed by ADR-0014. Setup uses the public REST frontdoor. Assertions use only UI output.
 */

import { expect } from '@playwright/test';
import { When, Then } from '../support/fixtures';

When('I open the campaign {string}', async ({ page, frontdoorApi, world }, title: string) => {
  const campaigns = await frontdoorApi.listCampaigns(world.currentUser?.token);
  const match = campaigns.find((c) => c.title === title);
  expect(match, `campaign "${title}" must exist`).toBeDefined();
  await page.goto(`#/campaigns/${match!.id}`);
  await page.waitForLoadState('domcontentloaded');
});

Then('the header shows {string}', async ({ page }, title: string) => {
  await expect(page.locator('runefoble-campaign-nav button.badge-live', { hasText: title })).toBeVisible({ timeout: 10_000 });
});

Then('the campaign switcher lists {string} and {string}', async ({ page }, first: string, second: string) => {
  await page.locator('runefoble-campaign-nav button.badge-live').click();
  const items = page.locator('runefoble-campaign-nav .campaign-item');
  await expect(items).toHaveText([first, second], { timeout: 10_000 });
});
