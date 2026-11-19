/**
 * DM Battlemap Set-Up Steps (TASK-0922).
 *
 * The DM sets up the session board through the "Set up battlemap" control of
 * `<runefoble-board-empty>`. The control creates the board and places one token for each seated
 * character through the gateway. The player browser reads the board after the `board_ready`
 * session frame. Governed by ADR-0013, ADR-0014, ADR-0015 and Hard Invariant 7. No step
 * creates a board or a token through the API.
 */

import { expect, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';
import { boardCell, boardToken } from '../support/board_cells';

const EMPTY_BOARD = 'runefoble-board-empty';
const SET_UP_LABEL = 'Set up battlemap';

async function clickSetUp(evelyn: Page, label: string): Promise<void> {
  const button = evelyn.locator(EMPTY_BOARD).getByRole('button', { name: label, exact: true });
  await expect(button, 'The DM must see the set-up control').toBeVisible({ timeout: 15_000 });
  await button.click();
}

async function expectBoardOnBothScreens(evelyn: Page, valeros: Page): Promise<void> {
  await expect(evelyn.locator('runefoble-board')).toBeVisible({ timeout: 15_000 });
  await expect(valeros.locator('runefoble-board')).toBeVisible({ timeout: 15_000 });
}

Then('Valeros sees {string} with no set-up control', async ({ world }, title: string) => {
  const empty = world.getPage('valeros').locator(EMPTY_BOARD);
  await expect(empty.getByRole('status')).toContainText(title, { timeout: 15_000 });
  await expect(empty.getByRole('button', { name: SET_UP_LABEL })).toHaveCount(0);
});

When('Evelyn clicks {string} on the empty board', async ({ world }, label: string) => {
  await clickSetUp(world.getPage('evelyn'), label);
});

Then(
  'the board on both screens shows the tokens {string} and {string}',
  async ({ world }, first: string, second: string) => {
    for (const persona of ['evelyn', 'valeros']) {
      const board = world.getPage(persona).locator('runefoble-board');
      await expect(boardToken(board, first), `${persona} must see ${first}`).toHaveCount(1, { timeout: 15_000 });
      await expect(boardToken(board, second), `${persona} must see ${second}`).toHaveCount(1, { timeout: 15_000 });
    }
  }
);

Given('Evelyn launches the session and sets up the battlemap', async ({ world }) => {
  const evelyn = world.getPage('evelyn');
  const valeros = world.getPage('valeros');
  const launch = evelyn.locator('runefoble-session-lobby').getByRole('button', { name: 'Launch Session' });
  await expect(launch, 'Launch control must be visible to the DM').toBeVisible({ timeout: 10_000 });
  await launch.click();
  await expect.poll(() => valeros.evaluate(() => window.location.hash), { timeout: 15_000 }).toContain('/sessions/');
  await clickSetUp(evelyn, SET_UP_LABEL);
  await expectBoardOnBothScreens(evelyn, valeros);
});

When(
  /Valeros drags his token "([^"]+)" to coordinate \((\d+), (\d+)\)/,
  async ({ world }, tokenName: string, toXStr: string, toYStr: string) => {
    const valerosPage = world.getPage('valeros');
    const board = valerosPage.locator('runefoble-board');
    const grid = board.locator('.grid');
    await expect(grid).toBeVisible({ timeout: 10_000 });

    const token = boardToken(grid, tokenName);
    const targetCell = boardCell(grid, parseInt(toXStr, 10), parseInt(toYStr, 10));
    await expect(token).toBeVisible({ timeout: 10_000 });
    await expect(targetCell).toBeVisible({ timeout: 10_000 });
    await expect(targetCell.locator('.token'), 'The target cell must be free').toHaveCount(0);

    const srcBox = await token.boundingBox();
    const destBox = await targetCell.boundingBox();
    expect(srcBox, 'Source token must have a layout box').not.toBeNull();
    expect(destBox, 'Target cell must have a layout box').not.toBeNull();
    await valerosPage.mouse.move(srcBox!.x + srcBox!.width / 2, srcBox!.y + srcBox!.height / 2);
    await valerosPage.mouse.down();
    await valerosPage.mouse.move(destBox!.x + destBox!.width / 2, destBox!.y + destBox!.height / 2, { steps: 5 });
    await valerosPage.mouse.up();

    // The drag is the only action. Its success is checked through the board.
    await expect(boardToken(targetCell, tokenName)).toBeVisible({ timeout: 10_000 });
  }
);
