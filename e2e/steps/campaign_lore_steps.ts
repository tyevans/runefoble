/**
 * Runefoble Campaign Atlas and Lore Codex Playwright BDD Step Definitions (TASK-0695).
 *
 * Preconditions use public frontdoors only: campaign creation, codex publishing, and the atlas
 * read go through the gateway. The pin is placed through the atlas UI. A failed precondition
 * throws with the response body. Governed by ADR-0013, ADR-0014, and Hard Invariant 7.
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

function requireCampaignId(campaignId: string | null): string {
  if (!campaignId) throw new Error('No campaign id. Create the campaign with a setup step first.');
  return campaignId;
}

function requireToken(token: string | undefined): string {
  if (!token) throw new Error('No bearer token. Log in with a setup step first.');
  return token;
}

Given(
  'the party has published the codex entry {string} with privacy {string}',
  async ({ frontdoorApi, world }, title: string, privacy: string) => {
    const campaignId = requireCampaignId(world.campaignId);
    const token = requireToken(world.currentUser?.token);
    if (privacy !== 'private' && privacy !== 'party_shared' && privacy !== 'public') {
      throw new Error(`Unknown codex privacy "${privacy}".`);
    }
    await frontdoorApi.publishCodexEntry(
      campaignId,
      { title, content: `Lore for ${title}.`, privacy },
      token
    );
  }
);

When('I open the Codex & Lore tab of the campaign', async ({ page, world }) => {
  const campaignId = requireCampaignId(world.campaignId);
  await page.goto(`#/campaigns/${campaignId}/codex`);
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('runefoble-campaign-atlas')).toBeVisible({ timeout: 15_000 });
});

When('I select the {string} view', async ({ page }, viewName: string) => {
  await page.getByRole('tab', { name: viewName }).click();
});

When('I click an empty spot on the campaign atlas', async ({ page }) => {
  await page.locator('runefoble-campaign-atlas .canvas-container').click({ position: { x: 240, y: 160 } });
});

When('I enter {string} as the pin title', async ({ page }, title: string) => {
  await page.locator('runefoble-campaign-atlas input[name="title"]').fill(title);
});

Then('the campaign atlas lists the pin {string}', async ({ page }, title: string) => {
  await expect(
    page.locator('runefoble-campaign-atlas text.pin-label', { hasText: title })
  ).toBeVisible({ timeout: 15_000 });
});

Then('the gateway atlas route lists the pin {string}', async ({ frontdoorApi, world }, title: string) => {
  const atlas = await frontdoorApi.getAtlas(requireCampaignId(world.campaignId), requireToken(world.currentUser?.token));
  expect(atlas.pins.map((pin) => pin.title)).toContain(title);
});

Then('the lore codex lists the entry {string}', async ({ page }, title: string) => {
  await expect(
    page.locator('runefoble-campaign-codex .entry-title', { hasText: title })
  ).toBeVisible({ timeout: 15_000 });
});
