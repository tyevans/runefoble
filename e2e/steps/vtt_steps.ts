/**
 * Runefoble Session Lobby & Tabletop VTT Playwright BDD Step Definitions
 *
 * Automates multi-browser testing across Dungeon Master and Player contexts
 * over real WebSockets per ADR-0004, ADR-0005, ADR-0010, ADR-0014, and Hard Invariant 7.
 * The Background steps in `vtt_setup_steps.ts` create the campaign, session and seats (TASK-0652).
 */

import { expect, type Locator, type Page } from '@playwright/test';
import { When, Then } from '../support/fixtures';
import { fillRouteTemplate, requireValue } from '../support/guards';
import { boardCell } from '../support/board_cells';
import { lobbyRoute, personaToken } from '../support/lobby_session';

/** The lobby card of one participant. Strict mode fails the step when the name matches no card or several cards. */
function participantCard(lobby: Locator, name: string): Locator {
  return lobby.locator('.participant-card').filter({
    has: lobby.page().locator('.username', { hasText: new RegExp(name, 'i') }),
  });
}


When('Valeros checks {string}', async ({ world }, controlLabel: string) => {
  const lobby = world.getPage('valeros').locator('runefoble-session-lobby');
  // Valeros's own card carries the `current-user` class. Only that card has his controls.
  const checkbox = lobby
    .locator('.participant-card.current-user')
    .getByRole('checkbox', { name: controlLabel, exact: true });
  await expect(checkbox).toHaveCount(1, { timeout: 10_000 });
  await checkbox.check();
});

Then(
  "Evelyn's lobby view updates in real time showing Valeros as {string}",
  async ({ world }, expectedStatus: string) => {
    const lobby = world.getPage('evelyn').locator('runefoble-session-lobby');

    const valerosCard = participantCard(lobby, 'Valeros');
    await expect(valerosCard).toBeVisible({ timeout: 10_000 });

    const badge = valerosCard.locator('.badge-readiness');
    await expect(badge).toHaveText(expectedStatus, { timeout: 10_000 });
  }
);

When(
  'Sarah opens {string} and checks {string}',
  async ({ world }, sessionTitle: string, controlLabel: string) => {
    // Sarah signed in and took a seat in the Background. Her browser opens the lobby now.
    const sarahPage = world.getPage('sarah');
    await sarahPage.goto(lobbyRoute(world, sessionTitle));
    await sarahPage.waitForLoadState('domcontentloaded');

    const lobby = sarahPage.locator('runefoble-session-lobby');
    await expect(lobby).toBeVisible({ timeout: 15_000 });

    // The control must be on Sarah's own card. A missing card fails the step.
    const sarahCard = participantCard(lobby, 'Sarah');
    await expect(sarahCard, "Sarah's participant card must be in the lobby").toBeVisible({ timeout: 10_000 });
    const checkbox = sarahCard.getByRole('checkbox', { name: controlLabel, exact: true });
    await expect(checkbox).toHaveCount(1, { timeout: 10_000 });
    await checkbox.check();
  }
);

Then(
  'the participant card displays the {string} badge across all connected screens',
  async ({ world }, badgeName: string) => {
    const pages: Page[] = ['evelyn', 'valeros', 'sarah'].map((name) => world.getPage(name));

    for (const p of pages) {
      const sarahCard = participantCard(p.locator('runefoble-session-lobby'), 'Sarah');
      await expect(sarahCard.locator('.badge-readiness')).toHaveText(badgeName, { timeout: 10_000 });
    }
  }
);

When('Evelyn clicks {string}', async ({ world }, buttonName: string) => {
  const btn = world
    .getPage('evelyn')
    .locator('runefoble-session-lobby')
    .getByRole('button', { name: buttonName });
  await expect(btn).toHaveCount(1, { timeout: 10_000 });
  await btn.click();
});

Then(
  "both Evelyn and Valeros's browsers navigate automatically to {string}",
  async ({ world }, hashTemplate: string) => {
    // The feature text names the route shape. The ids come from the Background setup replies.
    const expectedHash = fillRouteTemplate(hashTemplate, {
      campaignId: world.campaignId,
      sessionId: world.sessionId,
    });
    const evelynPage = world.getPage('evelyn');
    const valerosPage = world.getPage('valeros');

    await expect
      .poll(async () => evelynPage.evaluate(() => window.location.hash), { timeout: 15_000 })
      .toBe(expectedHash);
    await expect
      .poll(async () => valerosPage.evaluate(() => window.location.hash), { timeout: 15_000 })
      .toBe(expectedHash);
  }
);

Then(
  'the gateway reports the session status as {string}',
  async ({ frontdoorApi, world }, expected: string) => {
    // The launch control calls the start route. The owner moves the session out of the lobby (TASK-0910).
    const token = personaToken(world, 'evelyn');
    const sessionId = requireValue(world.sessionId, 'The Background created no session.');
    await expect
      .poll(async () => frontdoorApi.getSessionStatus(sessionId, token), { timeout: 10_000 })
      .toBe(expected);
  }
);

Then(
  'the tactical board {string} renders with dynamic grid bounds',
  async ({ world }, boardTag: string) => {
    const tagName = boardTag.replace(/[<>]/g, '');
    const evelynPage = world.getPage('evelyn');
    const valerosPage = world.getPage('valeros');

    const evelynBoard = evelynPage.locator(tagName);
    const valerosBoard = valerosPage.locator(tagName);

    await expect(evelynBoard).toBeVisible({ timeout: 10_000 });
    await expect(valerosBoard).toBeVisible({ timeout: 10_000 });

    const evelynGrid = evelynBoard.locator('.grid');
    await expect(evelynGrid).toBeVisible({ timeout: 10_000 });
    const cellsCount = await evelynGrid.locator('.cell').count();
    expect(cellsCount).toBeGreaterThanOrEqual(16);
  }
);

Then(
  /the token coordinate on Evelyn's screen smoothly moves to \((\d+), (\d+)\)/,
  async ({ world }, toXStr: string, toYStr: string) => {
    const toX = parseInt(toXStr, 10);
    const toY = parseInt(toYStr, 10);
    const evelynPage = world.getPage('evelyn');
    const board = evelynPage.locator('runefoble-board');
    await expect(board).toBeVisible({ timeout: 10_000 });

    const targetCell = boardCell(board, toX, toY);

    await expect(targetCell.locator('.token')).toBeVisible({ timeout: 10_000 });
  }
);

Then('the chronicle feed logs the move action', async ({ world }) => {
  const evelynPage = world.getPage('evelyn');
  const watcherFeed = evelynPage.locator('runefoble-watcher-feed');
  await expect(watcherFeed).toBeVisible({ timeout: 10_000 });

  // Justified .first(): the feed is append-only. A session can hold earlier move entries,
  // and the step asserts that at least one move entry exists.
  const moveEventItem = watcherFeed
    .locator('.event-item')
    .filter({ hasText: /moved to/i })
    .first();
  await expect(moveEventItem).toBeVisible({ timeout: 10_000 });
});
