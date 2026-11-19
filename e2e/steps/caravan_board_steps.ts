/**
 * Caravan Board Playwright BDD Step Definitions
 *
 * Drives <runefoble-caravan-board> through its UI. The only fault injection is a
 * 503 response at the network boundary, used to prove the error path (ADR-0015).
 * Governed by ADR-0014 and Hard Invariant 7. TASK-0677, TASK-0807.
 */

import { expect, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import type { FrontdoorApi } from '../support/frontdoor_api';
import type { World } from '../support/world';

const CARD = 'runefoble-caravan-contract-card';

Given('the caravan board is open', async ({ page, frontdoorApi, world }) => {
  const token = world.currentUser?.token;
  const campaign = await frontdoorApi.createCampaign('Amber Vanguard', { token });
  const sharedWorld = await frontdoorApi.createSharedWorld('Ashen Frontier', token);
  world.campaignId = campaign.id;
  world.customState.set('sharedWorldId', sharedWorld.shared_world_id);
  await page.goto(`#/caravans/${sharedWorld.shared_world_id}?campaign=${campaign.id}`);
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

/** Parses "Origin to Destination" into the two outposts of a contract title. */
function outpostsFromTitle(title: string): { origin: string; destination: string } {
  const [origin, destination] = title.split(' to ');
  if (!origin || !destination) throw new Error(`Contract title must read "Origin to Destination": ${title}`);
  return { origin, destination };
}

/** Posts a contract, accepts it for the open campaign, and optionally dispatches it. Then reloads the board. */
async function seedContract(
  { page, frontdoorApi, world }: { page: Page; frontdoorApi: FrontdoorApi; world: World },
  title: string,
  dispatch: boolean
): Promise<void> {
  const token = world.currentUser?.token;
  const sharedWorldId = world.customState.get('sharedWorldId') as string;
  const campaignId = world.campaignId as string;
  const { origin, destination } = outpostsFromTitle(title);
  const posted = await frontdoorApi.postCaravanContract(
    sharedWorldId,
    {
      origin_outpost: origin,
      destination_outpost: destination,
      cargo: { medicinal_herbs: 40, refined_iron: 20 },
      cargo_value: 600,
      route_risk_level: 'medium',
      transit_stages: 1,
      escort_collateral: 100,
      reward_gold: 300,
      reward_reputation: 20,
      posted_by_campaign_id: campaignId,
    },
    token
  );
  const contractId = posted.contract.contract_id;
  await frontdoorApi.acceptCaravanContract(
    sharedWorldId,
    contractId,
    { contractor_campaign_id: campaignId, contractor_party_name: 'Val\'s Freeblades' },
    token
  );
  if (dispatch) {
    await frontdoorApi.dispatchCaravanContract(
      sharedWorldId,
      contractId,
      { dispatched_by_campaign_id: campaignId },
      token
    );
  }
  await page.reload();
  await page.waitForSelector('runefoble-caravan-board', { timeout: 15_000 });
  await page.waitForSelector(`${CARD} .status-badge`, { timeout: 15_000 });
}

Given('an accepted caravan contract {string} is on the board', async ({ page, frontdoorApi, world }, title: string) => {
  await seedContract({ page, frontdoorApi, world }, title, false);
});

Given('a caravan contract {string} is in transit on the board', async ({ page, frontdoorApi, world }, title: string) => {
  await seedContract({ page, frontdoorApi, world }, title, true);
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
