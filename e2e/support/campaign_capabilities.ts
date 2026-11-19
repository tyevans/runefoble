/**
 * Campaign capabilities reply that the App Shell reads (TASK-0840).
 *
 * Steps that check a role-gated control record this reply, so the assertion compares the visible
 * control with the server flag. The reply comes from the public gateway route
 * `GET /api/v1/campaigns/{campaign_id}/capabilities`. The suite never builds it.
 */

import { expect, type Page } from '@playwright/test';
import type { World } from './world';

export interface CampaignCapabilities {
  manage: boolean;
  run_session: boolean;
  play: boolean;
  view: boolean;
}

const CAPABILITIES_KEY = 'campaignCapabilities';

/**
 * Opens an App Shell hash route and records the capabilities reply for the campaign.
 * Throws when the reply does not arrive or is not a success.
 */
export async function openAndRecordCapabilities(
  page: Page,
  world: World,
  campaignId: string,
  hash: string
): Promise<void> {
  const capabilitiesPath = `/api/v1/campaigns/${campaignId}/capabilities`;
  const capabilitiesReply = page.waitForResponse(
    (response) => response.request().method() === 'GET' && new URL(response.url()).pathname === capabilitiesPath,
    { timeout: 15_000 }
  );
  await page.goto(hash);
  await page.waitForLoadState('domcontentloaded');
  const reply = await capabilitiesReply;
  expect(reply.ok(), `${capabilitiesPath} answered ${reply.status()}`).toBe(true);
  world.set(CAPABILITIES_KEY, (await reply.json()) as CampaignCapabilities);
}

/** The capabilities reply that the last `openAndRecordCapabilities` call recorded. */
export function recordedCapabilities(world: World): CampaignCapabilities {
  const capabilities = world.get<CampaignCapabilities>(CAPABILITIES_KEY);
  if (!capabilities) throw new Error('No capabilities reply was recorded. Open the campaign or lobby route first.');
  return capabilities;
}
