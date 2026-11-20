/**
 * Typed Command Steps (TASK-0945).
 *
 * Valeros types a command in `<runefoble-command-bar>`. The App Shell posts it to the gateway
 * speak-and-act route. The Watcher stages a ghost preview on the board sockets, and Valeros
 * confirms it on `<runefoble-board>`. Every step uses the UI only. The fault step stops the-watcher
 * on Kind through a public make target. Governed by ADR-0013, ADR-0014, ADR-0022 (c) and
 * Hard Invariant 7. Playwright CSS locators pierce the open Shadow DOM.
 */

import { expect, type Locator, type Page } from '@playwright/test';
import { After, Given, When, Then } from '../support/fixtures';
import { boardCell, boardToken } from '../support/board_cells';
import { exactText } from '../support/guards';
import { startService, stopService } from '../support/service_faults';

const BOTH_SCREENS = ['evelyn', 'valeros'];

function commandBar(page: Page): Locator {
  return page.locator('runefoble-command-bar');
}

function commandInput(page: Page): Locator {
  return commandBar(page).getByRole('textbox', { name: 'Command' });
}

function ghostBanner(page: Page): Locator {
  return page.locator('runefoble-board').locator('.ghost-banner');
}

Then(
  /^the token "([^"]+)" is at \((\d+), (\d+)\) on both screens$/,
  async ({ world }, tokenName: string, xStr: string, yStr: string) => {
    for (const persona of BOTH_SCREENS) {
      const board = world.getPage(persona).locator('runefoble-board');
      const cell = boardCell(board, parseInt(xStr, 10), parseInt(yStr, 10));
      await expect(boardToken(cell, tokenName), `${persona} must see ${tokenName} at (${xStr}, ${yStr})`).toHaveCount(1, { timeout: 15_000 });
    }
  }
);

When(
  'Valeros types {string} in the command bar and presses Enter',
  async ({ world }, transcript: string) => {
    const input = commandInput(world.getPage('valeros'));
    // The input is enabled once the board shows the token of Valeros's character.
    await expect(input, 'The command input must be enabled').toBeEnabled({ timeout: 15_000 });
    await input.fill(transcript);
    await input.press('Enter');
  }
);

Then(
  /^the ghost banner on both screens says "([^"]+)" moves to \((\d+), (\d+)\)$/,
  async ({ world }, tokenName: string, xStr: string, yStr: string) => {
    for (const persona of BOTH_SCREENS) {
      await expect(ghostBanner(world.getPage(persona)), `${persona} must see the ghost banner`).toContainText(
        `${tokenName} moves to (${xStr}, ${yStr})`,
        { timeout: 15_000 }
      );
    }
  }
);

When('Valeros confirms the ghost preview', async ({ world }) => {
  const confirm = ghostBanner(world.getPage('valeros')).getByRole('button', { name: /Confirm Move/ });
  await expect(confirm).toBeVisible({ timeout: 10_000 });
  await confirm.click();
});

Then('the command bar answers the command', async ({ world }) => {
  // The bar shows The Watcher reply or the error of the call. It does not stay in the sending state.
  const answer = commandBar(world.getPage('valeros')).locator('.status.reply, .status.error');
  await expect(answer).toBeVisible({ timeout: 15_000 });
  await expect(answer).not.toHaveText('');
});

Then("no ghost banner appears on Valeros's screen", async ({ world }) => {
  // The reply arrived first, and a staged preview reaches the board socket before the reply.
  await expect(ghostBanner(world.getPage('valeros'))).toHaveCount(0);
});

Given('The Watcher service is stopped', async ({ world }) => {
  await world.getPage('valeros').waitForLoadState('networkidle');
  stopService('the_watcher');
});

// Restarts the-watcher after a journey that stopped it, so later journeys find the service.
After({ tags: '@watcher-down' }, async () => {
  startService('the_watcher');
});

Then('the command bar shows an error with status {int}', async ({ world }, status: number) => {
  const alert = commandBar(world.getPage('valeros')).getByRole('alert');
  await expect(alert).toContainText(`HTTP ${status}:`, { timeout: 15_000 });
});

Then('the command bar keeps the text {string}', async ({ world }, transcript: string) => {
  await expect(commandInput(world.getPage('valeros'))).toHaveValue(exactText(transcript));
});
