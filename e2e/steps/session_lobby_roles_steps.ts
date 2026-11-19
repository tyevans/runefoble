/**
 * Session Lobby Role Gate and Seat Step Definitions (TASK-0840, TASK-0889).
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

// TASK-0889: a campaign player takes a lobby seat through the gateway join route.

const INVITE_KEY = 'campaignInviteToken';

Given('the DM issues a player invite to the campaign', async ({ frontdoorApi, world }) => {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "campaign {string} exists" first.');
  const token = requireValue(world.currentUser?.token, 'No bearer token. Log in with a setup step first.');
  const invite = await frontdoorApi.createCampaignInvite(campaignId, 'player', token);
  world.set(INVITE_KEY, requireValue(invite.token, 'The invite reply has no token.'));
});

Given('I redeem the campaign invite', async ({ frontdoorApi, world }) => {
  const invite = requireValue(world.get<string>(INVITE_KEY), 'No invite. Run "the DM issues a player invite" first.');
  const token = requireValue(world.currentUser?.token, 'No bearer token. Log in with a setup step first.');
  const joined = await frontdoorApi.joinCampaign(invite, token);
  expect(joined.role).toBe('player');
});

Given('I have a character named {string}', async ({ frontdoorApi, world }, name: string) => {
  const token = requireValue(world.currentUser?.token, 'No bearer token. Log in with a setup step first.');
  const created = await frontdoorApi.createCharacter(
    { name, characterClass: 'Ranger', level: 3, maxHp: 24, currentHp: 24, armorClass: 15, speed: 30 },
    token
  );
  world.characterId = requireValue(created.id, 'The character reply has no id.');
});

When('I take a seat with my character', async ({ page, world }) => {
  const sessionId = requireValue(world.sessionId, 'No session. Run "the DM creates session" first.');
  const characterId = requireValue(world.characterId, 'No character. Run "I have a character named" first.');
  await page.locator(`${LOBBY} select.seat-character-select`).selectOption(characterId);
  const joinPath = `/api/v1/sessions/${sessionId}/join`;
  const joinReply = page.waitForResponse(
    (response) => response.request().method() === 'POST' && new URL(response.url()).pathname === joinPath,
    { timeout: 15_000 }
  );
  await page.locator(`${LOBBY} button.btn-take-seat`).click();
  const reply = await joinReply;
  expect(reply.ok(), `${joinPath} answered ${reply.status()}`).toBe(true);
  await expect(page.locator(`${LOBBY} button.btn-take-seat`)).toHaveCount(0, { timeout: 10_000 });
});

When('I mark myself ready to play', async ({ page }) => {
  await page.locator(`${LOBBY} .participant-card.current-user input.checkbox-ready`).check();
});
