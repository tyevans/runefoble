/**
 * Runefoble Session Lobby & Tabletop VTT Playwright BDD Step Definitions
 *
 * Automates multi-browser testing across Dungeon Master and Player contexts
 * over real WebSockets per ADR-0004, ADR-0005, ADR-0010, ADR-0014, and Hard Invariant 7.
 */

import { expect, test, type Locator, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { exactText, requireValue, sessionIdFromTitle } from '../support/guards';
import type { World } from '../support/world';

function lobbyRoute(world: World, sessionTitle: string): string {
  const campaignId = requireValue(world.campaignId, 'No campaign. Run "Evelyn is hosting session" first.');
  return `#/campaigns/${campaignId}/lobby/${sessionIdFromTitle(sessionTitle)}`;
}

/** The lobby card of one participant. Strict mode fails the step when the name matches no card or several cards. */
function participantCard(lobby: Locator, name: string): Locator {
  return lobby.locator('.participant-card').filter({
    has: lobby.page().locator('.username', { hasText: new RegExp(name, 'i') }),
  });
}

/** The board cell whose coordinate label is exactly `x,y`. */
function boardCell(board: Locator, x: number, y: number): Locator {
  return board
    .locator('.cell')
    .filter({ has: board.page().locator('.coord-label', { hasText: exactText(`${x},${y}`) }) });
}

Given(
  'Evelyn is hosting session {string} for campaign {string}',
  async ({ auth, world, page }, sessionTitle: string, campaignId: string) => {
    const evelynUser = await auth.signInAs('evelyn', page);
    world.currentUser = evelynUser;
    world.setPage('evelyn', page);
    world.campaignId = campaignId;

    const sessionId = sessionIdFromTitle(sessionTitle);
    world.sessionId = sessionId;

    await page.goto(`#/campaigns/${campaignId}/lobby/${sessionId}`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('runefoble-session-lobby')).toBeVisible({ timeout: 15_000 });
  }
);

Given(
  'Valeros joins {string} in a separate browser',
  async ({ browser, auth, world }, sessionTitle: string) => {
    const route = lobbyRoute(world, sessionTitle);

    const valerosContext = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    world.extraContexts.push(valerosContext);
    const valerosPage = await valerosContext.newPage();
    world.setPage('valeros', valerosPage);

    await auth.signInAs('valeros', valerosPage);
    await valerosPage.goto(route);
    await valerosPage.waitForLoadState('domcontentloaded');
    await expect(valerosPage.locator('runefoble-session-lobby')).toBeVisible({ timeout: 15_000 });
  }
);

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
  async ({ browser, auth, world }, sessionTitle: string, controlLabel: string) => {
    const route = lobbyRoute(world, sessionTitle);

    const sarahContext = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    world.extraContexts.push(sarahContext);
    const sarahPage = await sarahContext.newPage();
    world.setPage('sarah', sarahPage);

    await auth.signInAs('sarah', sarahPage);
    await sarahPage.goto(route);
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
  async ({ world }, expectedHash: string) => {
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

When(
  /Valeros drags his token from coordinate \((\d+), (\d+)\) to \((\d+), (\d+)\)/,
  async ({ world }, fromXStr: string, fromYStr: string, toXStr: string, toYStr: string) => {
    const fromX = parseInt(fromXStr, 10);
    const fromY = parseInt(fromYStr, 10);
    const toX = parseInt(toXStr, 10);
    const toY = parseInt(toYStr, 10);
    const valerosPage = world.getPage('valeros');
    const evelynPage = world.getPage('evelyn');

    // Launch through the DM's visible control. Valeros's browser follows the
    // session route on its own (see "both Evelyn and Valeros's browsers navigate").
    const evelynHash = await evelynPage.evaluate(() => window.location.hash);
    if (!evelynHash.includes('/sessions/')) {
      const launchBtn = evelynPage
        .locator('runefoble-session-lobby')
        .getByRole('button', { name: 'Launch Session' });
      await expect(launchBtn, 'Launch control must be visible to the DM').toBeVisible({
        timeout: 10_000,
      });
      await launchBtn.click();
    }

    await expect(valerosPage.locator('runefoble-board')).toBeVisible({ timeout: 15_000 });
    await expect(evelynPage.locator('runefoble-board')).toBeVisible({ timeout: 15_000 });
    await expect(evelynPage.locator('runefoble-watcher-feed')).toBeVisible({ timeout: 15_000 });

    const board = valerosPage.locator('runefoble-board');
    const grid = board.locator('.grid');
    await expect(grid).toBeVisible({ timeout: 10_000 });

    const sourceCell = boardCell(grid, fromX, fromY);
    const targetCell = boardCell(grid, toX, toY);
    await expect(sourceCell).toBeVisible({ timeout: 10_000 });
    await expect(targetCell).toBeVisible({ timeout: 10_000 });

    // A cell holds at most one token (board_state cell template).
    const token = sourceCell.locator('.token');
    await expect(token).toBeVisible({ timeout: 10_000 });

    const srcBox = await token.boundingBox();
    const destBox = await targetCell.boundingBox();
    expect(srcBox, 'Source token must have a layout box').not.toBeNull();
    expect(destBox, 'Target cell must have a layout box').not.toBeNull();
    await valerosPage.mouse.move(srcBox!.x + srcBox!.width / 2, srcBox!.y + srcBox!.height / 2);
    await valerosPage.mouse.down();
    await valerosPage.mouse.move(destBox!.x + destBox!.width / 2, destBox!.y + destBox!.height / 2, {
      steps: 5,
    });
    await valerosPage.mouse.up();

    // The drag is the only action. Its success is checked through the board.
    await expect(targetCell.locator('.token')).toBeVisible({ timeout: 10_000 });
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
