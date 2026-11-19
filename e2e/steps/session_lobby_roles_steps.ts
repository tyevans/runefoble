/**
 * Session Lobby Role Gate Step Definitions (TASK-0840).
 *
 * Setup goes through public gateway routes only. The lobby step records the capabilities reply
 * that the App Shell reads, so each assertion compares the visible control with the server flag.
 * A missing control and a control shown by mistake both fail. Governed by ADR-0001, ADR-0014
 * and Hard Invariant 7. The steps never call a service directly.
 */

import { expect, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { openAndRecordCapabilities, recordedCapabilities } from '../support/campaign_capabilities';

const LOBBY = 'runefoble-session-lobby';
const LAUNCH_CONTROL = `${LOBBY} button.btn-launch`;

function requireValue(value: string | null | undefined, message: string): string {
  if (!value) throw new Error(message);
  return value;
}

/** Waits two animation frames, so the lobby renders the state that the last reply set. */
async function settleRender(page: Page): Promise<void> {
  await page.evaluate(
    () => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  );
}

Given(
  'the DM creates session {string} in that campaign',
  async ({ frontdoorApi, world }, title: string) => {
    const campaignId = requireValue(world.campaignId, 'No campaign. Run "campaign {string} exists" first.');
    const token = requireValue(world.currentUser?.token, 'No bearer token. Log in with a setup step first.');
    const session = await frontdoorApi.createCampaignSession(campaignId, title, token);
    world.sessionId = session.id;
  }
);

When('I open the lobby of session {string}', async ({ page, world }, title: string) => {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "campaign {string} exists" first.');
  const sessionId = requireValue(world.sessionId, `Session "${title}" was not set up in this scenario.`);
  await openAndRecordCapabilities(page, world, campaignId, `#/campaigns/${campaignId}/lobby/${sessionId}`);
  await expect(page.locator(`${LOBBY} .lobby-header`)).toBeVisible({ timeout: 15_000 });
  await settleRender(page);
});

Then('the server reports that I can run the session', async ({ world }) => {
  expect(recordedCapabilities(world).run_session).toBe(true);
});

Then('the server reports that I cannot run the session', async ({ world }) => {
  expect(recordedCapabilities(world).run_session).toBe(false);
});

Then('I see the Launch Session control', async ({ page }) => {
  await expect(page.locator(LAUNCH_CONTROL)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(LAUNCH_CONTROL)).toContainText('Launch Session');
});

Then('I do not see the Launch Session control', async ({ page }) => {
  await expect(page.locator(`${LOBBY} .readiness-summary-text`)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(LAUNCH_CONTROL)).toHaveCount(0);
});

Then('the lobby readiness summary reads {string}', async ({ page }, text: string) => {
  await expect(page.locator(`${LOBBY} .readiness-summary-text`)).toHaveText(text, { timeout: 10_000 });
});
