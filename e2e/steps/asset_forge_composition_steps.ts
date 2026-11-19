/**
 * App Shell Asset Forge Composition Step Definitions.
 *
 * Opens the forge tab of a campaign through the App Shell route and observes the
 * composed microfrontend elements. Setup goes through the public campaign API and
 * the page only. Governed by ADR-0013, ADR-0014, and Hard Invariant 7. TASK-0645.
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { requireValue } from '../support/guards';

function forgeHash(campaignId: string): string {
  return `#/campaigns/${campaignId}/forge`;
}

When('I open the forge tab of the campaign', async ({ page, world }) => {
  const campaignId = world.campaignId;
  if (!campaignId) {
    throw new Error('No campaign is set. Run "campaign {string} exists" first.');
  }
  await page.goto(forgeHash(campaignId));
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('runefoble-asset-forge', { timeout: 15_000 });
});

Then('the URL hash should be the forge tab of the campaign', async ({ page, world }) => {
  const campaignId = requireValue(world.campaignId, 'No campaign is set. Run "campaign {string} exists" first.');
  await expect
    .poll(async () => page.evaluate(() => window.location.hash), { timeout: 10_000 })
    .toBe(forgeHash(campaignId));
});

Then('the page contains the element {string}', async ({ page }, selector: string) => {
  await expect(page.locator(selector)).toBeVisible({ timeout: 15_000 });
});

Then('I should see the button {string}', async ({ page }, label: string) => {
  await expect(page.getByRole('button', { name: label })).toBeVisible({ timeout: 10_000 });
});

Then('the preview image is shown after the forge returns', async ({ page }) => {
  const preview = page.locator('img[alt="Forged Battlemap Preview"]');
  await expect(preview).toBeVisible({ timeout: 15_000 });
  await expect(preview).not.toHaveAttribute('src', '');
});
