/**
 * Session End and Recap Step Definitions (TASK-0953).
 *
 * Setup uses public gateway routes and the App Shell. The DM ends the session with the control
 * in the App Shell. Each assertion reads what a persona sees: the recap lines, the speaker and
 * the dice text. No step reads a service directly, and no step changes state behind the UI.
 * Governed by ADR-0014, ADR-0015 and Hard Invariant 7.
 */

import { expect, test, type Locator, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { requireValue } from '../support/guards';
import { lobbySessionId, personaToken, rememberPersonaToken } from '../support/lobby_session';
import { joinCampaignThroughInviteLink } from '../support/invite_join';
import type { World } from '../support/world';

const ROLLER = 'runefoble-dice-roller';
const FEED = 'runefoble-watcher-feed';
const RECAP = 'runefoble-session-recap';
const RECAP_LINE = `${RECAP} .recap-line`;
const END_BUTTON = 'End Session';

/** The character name that each persona's seat carries. The roller sends it as the speaker. */
const CHARACTER_NAMES: Record<string, string> = {
  valeros: 'Valeros the Bold',
};

function sessionHash(world: World): string {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
  const sessionId = requireValue(world.sessionId, 'No session. Run "Evelyn creates campaign" first.');
  return `#/campaigns/${campaignId}/sessions/${sessionId}`;
}

function sessionPath(world: World): string {
  return `/api/v1/sessions/${requireValue(world.sessionId, 'No session.')}`;
}

/** Opens the active session route in a persona's browser and waits for its feed. */
async function openActiveSession(page: Page, world: World): Promise<void> {
  await page.goto(sessionHash(world));
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator(FEED)).toBeVisible({ timeout: 15_000 });
}

/** A recap line that holds the text. */
function recapLine(page: Page, text: string): Locator {
  return page.locator(RECAP_LINE, { hasText: text }).first();
}

/** Types into the roller, sends the roll, and waits for the owner's reply before it returns. */
async function rollInDiceRoller(page: Page, world: World, formula: string): Promise<void> {
  const roll = `${sessionPath(world)}/roll`;
  await expect(page.locator(`${ROLLER} button.roll-action-btn`)).toHaveCount(1, { timeout: 10_000 });
  await page.locator(`${ROLLER} input.formula-input`).fill(formula);
  const reply = page.waitForResponse(
    (response) => response.request().method() === 'POST' && new URL(response.url()).pathname === roll,
    { timeout: 15_000 }
  );
  await page.locator(`${ROLLER} button.roll-action-btn`).click();
  const answer = await reply;
  expect(answer.ok(), `${roll} answered ${answer.status()}`).toBe(true);
}

/** Clicks End Session, confirms, and waits for the owner's reply and the recap. */
async function endSessionInTheUi(page: Page, world: World): Promise<void> {
  const end = `${sessionPath(world)}/end`;
  const endButton = page.getByRole('button', { name: END_BUTTON, exact: true });
  await expect(endButton).toHaveCount(1, { timeout: 10_000 });
  await endButton.click();
  const reply = page.waitForResponse(
    (response) => response.request().method() === 'POST' && new URL(response.url()).pathname === end,
    { timeout: 15_000 }
  );
  await page.getByRole('button', { name: 'Confirm End', exact: true }).click();
  const answer = await reply;
  expect(answer.ok(), `${end} answered ${answer.status()}`).toBe(true);
  await expect(page.locator(`${RECAP} .session-recap`)).toBeVisible({ timeout: 10_000 });
}

Given('Valeros redeems a player invite to the campaign in a browser', async ({ browser, auth, frontdoorApi, world }) => {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
  const dmToken = personaToken(world, 'evelyn');
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  world.extraContexts.push(context);
  const personaPage = await context.newPage();
  world.setPage('valeros', personaPage);
  const user = await auth.signInAs('valeros', personaPage);
  rememberPersonaToken(world, 'valeros', user.token);

  const invite = await frontdoorApi.createCampaignInvite(campaignId, 'player', dmToken);
  await joinCampaignThroughInviteLink(personaPage, requireValue(invite.token, 'The invite reply has no token.'));
});

When('{word} rolls {string} in the dice roller in the UI', async ({ world }, persona: string, formula: string) => {
  const page = world.getPage(persona.toLowerCase());
  await openActiveSession(page, world);
  await rollInDiceRoller(page, world, formula);
  // The roll is on the feed of the roller before the session ends. The recap reads it from the server.
  await expect(page.locator(`${FEED} .event-item`, { hasText: `${formula} = ` }).first()).toBeVisible({ timeout: 10_000 });
});

When('{word} clicks {string} and confirms', async ({ world }, persona: string, label: string) => {
  if (label !== END_BUTTON) throw new Error(`The control "${label}" is not the session end control.`);
  await endSessionInTheUi(world.getPage(persona.toLowerCase()), world);
});

When('{word} ends the session {string} in the UI', async ({ world }, persona: string, title: string) => {
  lobbySessionId(world, title);
  await endSessionInTheUi(world.getPage(persona.toLowerCase()), world);
});

When('{word} reloads the ended session view', async ({ world }, persona: string) => {
  const page = world.getPage(persona.toLowerCase());
  await page.reload();
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator(`${RECAP} .session-recap`)).toBeVisible({ timeout: 15_000 });
});

Then('{word} sees the recap with {string}', async ({ world }, persona: string, text: string) => {
  await expect(recapLine(world.getPage(persona.toLowerCase()), text)).toBeVisible({ timeout: 10_000 });
});

Then("{word}'s view shows the recap with {string} and {string}", async ({ world }, persona: string, first: string, second: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect(recapLine(page, first)).toBeVisible({ timeout: 10_000 });
  await expect(recapLine(page, second)).toBeVisible({ timeout: 10_000 });
});

Then("{word}'s view shows the recap within 10 seconds", async ({ world }, persona: string) => {
  await expect(world.getPage(persona.toLowerCase()).locator(`${RECAP} .session-recap`)).toBeVisible({ timeout: 10_000 });
});

Then('the recap of {word} lists the dice entry {string}', async ({ world }, persona: string, formula: string) => {
  const page = world.getPage(persona.toLowerCase());
  const speaker = requireValue(CHARACTER_NAMES[persona.toLowerCase()], `No character name for "${persona}".`);
  const entry = page.locator(RECAP_LINE, {
    has: page.locator('.speaker-name', { hasText: speaker }),
    hasText: formula,
  });
  await expect(entry.first()).toBeVisible({ timeout: 10_000 });
});

Then('{word} has no {string} control', async ({ world }, persona: string, label: string) => {
  const page = world.getPage(persona.toLowerCase());
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('button', { name: label, exact: true })).toHaveCount(0);
});
