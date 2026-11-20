/**
 * Joins a campaign through the invite link in the App Shell (TASK-0950, ADR-0023 e).
 *
 * The steps that need a signed-in persona use this helper, so no step calls the API join route.
 */

import { expect, type Page } from '@playwright/test';

const JOIN_BUTTON = 'Join campaign';

/** Opens `#/join/<token>` in a signed-in page, clicks the join button, and returns the campaign id. */
export async function joinCampaignThroughInviteLink(page: Page, inviteToken: string): Promise<string> {
  await page.goto(`/#/join/${inviteToken}`);
  const joinButton = page.locator('runefoble-campaign-join').getByRole('button', { name: JOIN_BUTTON, exact: true });
  await expect(joinButton).toBeVisible({ timeout: 15_000 });
  await joinButton.click();
  await expect
    .poll(async () => page.evaluate(() => window.location.hash), { timeout: 15_000 })
    .toMatch(/^#\/campaigns\/[^/]+$/);
  return page.evaluate(() => window.location.hash.replace(/^#\/campaigns\//, ''));
}
