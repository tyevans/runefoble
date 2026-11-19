/**
 * Campaign Rules Homebrew Playwright BDD Step Definitions (TASK-0878).
 *
 * Drives the campaign rules tab and its homebrew creator. Setup goes through public routes only:
 * the DM assigns the player role through the gateway, and the player signs in through Zitadel.
 * Governed by ADR-0014 and Hard Invariant 7. The steps never call a service directly.
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { findPersona, resolvePersonaKey } from '../support/personas';

const COMPENDIUM = 'runefoble-rules-compendium';
const HOMEBREW_CREATOR = 'runefoble-homebrew-creator';

function requireCampaignId(campaignId: string | null): string {
  if (!campaignId) throw new Error('No campaign id. Create the campaign with a setup step first.');
  return campaignId;
}

function requireToken(token: string | undefined): string {
  if (!token) throw new Error('No bearer token. Log in with a setup step first.');
  return token;
}

Given(
  'the {string} persona joins the campaign as a player',
  async ({ frontdoorApi, world }, roleOrName: string) => {
    const campaignId = requireCampaignId(world.campaignId);
    const token = requireToken(world.currentUser?.token);
    const persona = findPersona(resolvePersonaKey(roleOrName));
    await frontdoorApi.assignCampaignRole(campaignId, persona.userId, 'player', token);
  }
);

When('I open the Rules tab of the campaign', async ({ page, world }) => {
  const campaignId = requireCampaignId(world.campaignId);
  await page.goto(`#/campaigns/${campaignId}`);
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('tab', { name: 'Rules', exact: true }).click();
  await expect(page.locator(COMPENDIUM)).toBeVisible({ timeout: 15_000 });
});

When('I open the rules compendium tab {string}', async ({ page }, tabName: string) => {
  const tab = page.locator(`${COMPENDIUM} button.tab-btn`, { hasText: tabName });
  await tab.click();
});

When('I enter {string} as the homebrew monster title', async ({ page }, title: string) => {
  const input = page.locator(`${HOMEBREW_CREATOR} input[placeholder="e.g. Abyssal Stalker"]`);
  await expect(input).toBeVisible({ timeout: 10_000 });
  await input.fill(title);
});

Then('the homebrew form reports {string}', async ({ page }, text: string) => {
  const report = page.locator(HOMEBREW_CREATOR).getByText(text).first();
  await expect(report).toBeVisible({ timeout: 15_000 });
});
