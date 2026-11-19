/**
 * Campaign Header Step Definitions (TASK-0652).
 *
 * The campaign comes from the `campaign {string} exists` setup step, which calls the public
 * campaigns route. These steps open that campaign by the id from the reply and read the
 * title that the campaign header shows. Governed by ADR-0014 and Hard Invariant 7.
 */

import { expect } from '@playwright/test';
import { When, Then } from '../support/fixtures';
import { requireValue } from '../support/guards';

When('I open the campaign that setup created', async ({ page, world }) => {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "campaign {string} exists" first.');
  await page.goto(`#/campaigns/${campaignId}`);
  await page.waitForLoadState('domcontentloaded');
});

Then('the campaign header shows the title {string}', async ({ page }, title: string) => {
  const heading = page.locator('runefoble-campaign-header h1.campaign-title');
  await expect(heading).toHaveText(title, { timeout: 15_000 });
});
