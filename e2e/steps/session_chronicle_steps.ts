/**
 * Session Chronicle Feed Step Definitions (TASK-0641).
 *
 * Setup uses only public gateway routes (campaign, session, start). Assertions read the
 * observable feed rows in the App Shell. Governed by ADR-0011, ADR-0014, and Hard Invariant 7.
 */

import { expect } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

Given(
  'the DM creates and starts session {string} in that campaign',
  async ({ frontdoorApi, world }, title: string) => {
    const token = world.currentUser?.token;
    const campaignId = world.campaignId;
    if (!campaignId) throw new Error('No campaign in the world. Create one with "campaign {string} exists" first.');
    const session = await frontdoorApi.createCampaignSession(campaignId, title, token);
    await frontdoorApi.startSession(session.session_id, token);
    world.sessionId = session.session_id;
  }
);

When('I open session {string} in the App Shell', async ({ page, world }, title: string) => {
  const campaignId = world.campaignId;
  const sessionId = world.sessionId;
  if (!campaignId || !sessionId) throw new Error(`Session "${title}" was not set up in this scenario.`);
  await page.goto(`/#/campaigns/${campaignId}/sessions/${sessionId}`);
  await page.waitForLoadState('domcontentloaded');
});

Then('the session feed shows the entry {string}', async ({ page }, text: string) => {
  await expect(page.locator('runefoble-watcher-feed').getByText(text, { exact: true })).toBeVisible({
    timeout: 10_000,
  });
});
