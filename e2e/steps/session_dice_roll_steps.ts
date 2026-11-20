/**
 * Dice Roll Step Definitions (TASK-0951).
 *
 * Setup uses public gateway routes and the App Shell. A roll is made in the dice roller of the
 * App Shell, and the steps read the chronicle rows that the feed shows. Each assertion reads what
 * a player sees: the row, the speaker, the formula and the server total. No step reads a
 * service directly. Governed by ADR-0014, ADR-0015 and Hard Invariant 7.
 */

import { expect, test, type Locator, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { requireValue } from '../support/guards';
import { lobbySessionId, personaToken, rememberPersonaToken } from '../support/lobby_session';
import { joinCampaignThroughInviteLink } from '../support/invite_join';
import type { World } from '../support/world';

const FEED = 'runefoble-watcher-feed';
const ROLLER = 'runefoble-dice-roller';
const LAST_ROLL_KEY = 'lastDiceEntry';

/** The character name that each persona's seat carries. The roller sends it as the speaker. */
const CHARACTER_NAMES: Record<string, string> = {
  valeros: 'Valeros the Bold',
  sarah: 'Sarah of the Mists',
};

interface DiceEntry {
  speaker: string;
  text: string;
}

function sessionHash(world: World): string {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
  const sessionId = requireValue(world.sessionId, 'No session. Run "Evelyn creates campaign" first.');
  return `#/campaigns/${campaignId}/sessions/${sessionId}`;
}

function rollPath(world: World): string {
  return `/api/v1/sessions/${requireValue(world.sessionId, 'No session.')}/roll`;
}

/** Opens the active session route in a persona's browser and waits for its feed. */
async function openActiveSession(page: Page, world: World): Promise<void> {
  await page.goto(sessionHash(world));
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator(FEED)).toBeVisible({ timeout: 15_000 });
}

/** The feed rows that a speaker has. The row's last line is the dice text. */
function rowsOf(page: Page, speaker: string): Locator {
  return page.locator(`${FEED} .event-item`, { has: page.locator('.speaker-name', { hasText: speaker }) });
}

/** The dice text of the newest row of a speaker, or an empty string when there is no row. */
async function newestDiceText(page: Page, speaker: string): Promise<string> {
  const rows = rowsOf(page, speaker);
  if ((await rows.count()) === 0) return '';
  const lines = (await rows.last().innerText()).split('\n').map((line) => line.trim()).filter(Boolean);
  return lines.at(-1) ?? '';
}

/** Types into the roller, sends the roll, and waits for the owner's reply before it returns. */
async function rollInDiceRoller(page: Page, world: World, formula: string): Promise<void> {
  await page.locator(`${ROLLER} input.formula-input`).fill(formula);
  const reply = page.waitForResponse(
    (response) => response.request().method() === 'POST' && new URL(response.url()).pathname === rollPath(world),
    { timeout: 15_000 }
  );
  await page.locator(`${ROLLER} button.roll-action-btn`).click();
  const answer = await reply;
  expect(answer.ok(), `${rollPath(world)} answered ${answer.status()}`).toBe(true);
}

Given('Evelyn runs the active session {string} in the UI', async ({ world }, title: string) => {
  const page = world.getPage('evelyn');
  lobbySessionId(world, title);
  const launch = page.locator('runefoble-session-lobby').getByRole('button', { name: 'Launch Session' });
  await expect(launch).toHaveCount(1, { timeout: 10_000 });
  await launch.click();
  await expect(page.locator(FEED)).toBeVisible({ timeout: 15_000 });
});

When('{word} opens the active session in the UI', async ({ world }, persona: string) => {
  await openActiveSession(world.getPage(persona.toLowerCase()), world);
});

When('{word} types {string} into the formula field of the dice roller', async ({ world }, persona: string, formula: string) => {
  await world.getPage(persona.toLowerCase()).locator(`${ROLLER} input.formula-input`).fill(formula);
});

When('{word} clicks the roll button', async ({ world }, persona: string) => {
  const page = world.getPage(persona.toLowerCase());
  const reply = page.waitForResponse(
    (response) => response.request().method() === 'POST' && new URL(response.url()).pathname === rollPath(world),
    { timeout: 15_000 }
  );
  await page.locator(`${ROLLER} button.roll-action-btn`).click();
  const answer = await reply;
  expect(answer.ok(), `${rollPath(world)} answered ${answer.status()}`).toBe(true);
});

Given('{word} has rolled {string} in the session {string}', async ({ world }, persona: string, formula: string, title: string) => {
  lobbySessionId(world, title);
  const page = world.getPage(persona.toLowerCase());
  await rollInDiceRoller(page, world, formula);
  const speaker = requireValue(CHARACTER_NAMES[persona.toLowerCase()], `No character name for "${persona}".`);
  await expect.poll(() => newestDiceText(page, speaker), { timeout: 10_000 }).toMatch(/^1d20 = \d+$/);
  world.set(LAST_ROLL_KEY, { speaker, text: await newestDiceText(page, speaker) } satisfies DiceEntry);
});

Then('{word} sees a dice entry with the speaker {string} in the chronicle', async ({ world }, persona: string, speaker: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect.poll(() => newestDiceText(page, speaker), { timeout: 10_000 }).not.toBe('');
  world.set(LAST_ROLL_KEY, { speaker, text: await newestDiceText(page, speaker) } satisfies DiceEntry);
});

Then('{word} sees the same dice entry within 10 seconds', async ({ world }, persona: string) => {
  const entry = requireValue(world.get<DiceEntry>(LAST_ROLL_KEY), 'No dice entry was read. Run the step that reads it first.');
  const page = world.getPage(persona.toLowerCase());
  await expect.poll(() => newestDiceText(page, entry.speaker), { timeout: 10_000 }).toBe(entry.text);
});

Then('the dice entry shows the formula {string} and a total from {int} to {int}', async ({ world }, formula: string, low: number, high: number) => {
  const entry = requireValue(world.get<DiceEntry>(LAST_ROLL_KEY), 'No dice entry was read. Run the step that reads it first.');
  const match = entry.text.match(/^(.+) = (\d+)$/);
  if (!match) throw new Error(`The dice entry "${entry.text}" has no "formula = total" form.`);
  expect(match[1]).toBe(formula);
  const total = Number(match[2]);
  expect(total).toBeGreaterThanOrEqual(low);
  expect(total).toBeLessThanOrEqual(high);
});

When('{word} reloads the session view', async ({ world }, persona: string) => {
  const page = world.getPage(persona.toLowerCase());
  await page.reload();
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator(FEED)).toBeVisible({ timeout: 15_000 });
});

Then('{word} still sees the dice entry with the speaker {string} in the chronicle', async ({ world }, persona: string, speaker: string) => {
  const entry = requireValue(world.get<DiceEntry>(LAST_ROLL_KEY), 'No dice entry was read before the reload.');
  const page = world.getPage(persona.toLowerCase());
  await expect.poll(() => newestDiceText(page, speaker), { timeout: 10_000 }).toBe(entry.text);
});

// TASK-0951, scenario 3: a player with no bound character.

Given('{word} joins the campaign as a player with no character', async ({ browser, auth, frontdoorApi, world }, persona: string) => {
  const key = persona.toLowerCase();
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn creates campaign" first.');
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  world.extraContexts.push(context);
  const personaPage = await context.newPage();
  world.setPage(key, personaPage);
  const user = await auth.signInAs(key, personaPage);
  rememberPersonaToken(world, key, user.token);

  const invite = await frontdoorApi.createCampaignInvite(campaignId, 'player', personaToken(world, 'evelyn'));
  await joinCampaignThroughInviteLink(personaPage, requireValue(invite.token, 'The invite reply has no token.'));
});

Then('{word} sees the dice roller without a roll button', async ({ world }, persona: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect(page.locator(ROLLER)).toBeVisible({ timeout: 10_000 });
  await expect(page.locator(`${ROLLER} button.roll-action-btn`)).toHaveCount(0);
});

Then('{word} sees the dice roller say {string}', async ({ world }, persona: string, text: string) => {
  const page = world.getPage(persona.toLowerCase());
  await expect(page.locator(`${ROLLER} [role="status"]`)).toContainText(text, { timeout: 10_000 });
});
