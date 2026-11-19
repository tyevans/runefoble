/**
 * Runefoble Session Lobby & Tabletop VTT Playwright BDD Step Definitions
 *
 * Automates multi-browser testing across Dungeon Master and Player contexts
 * over real WebSockets per ADR-0004, ADR-0005, ADR-0010, ADR-0014, and Hard Invariant 7.
 */

import { expect, test, type Page } from '@playwright/test';
import { Given, When, Then } from '../support/fixtures';

Given(
  'Evelyn is hosting session {string} for campaign {string}',
  async ({ auth, world, page }, sessionTitle: string, campaignId: string) => {
    const evelynUser = await auth.injectUserIntoPage(page, 'evelyn');
    world.currentUser = evelynUser;
    world.setPage('evelyn', page);
    world.campaignId = campaignId;

    const sessionIdMatch = sessionTitle.match(/\d+/);
    const sessionId = sessionIdMatch ? sessionIdMatch[0] : '15';
    world.sessionId = sessionId;

    await page.goto(`#/campaigns/${campaignId}/lobby/${sessionId}`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('runefoble-session-lobby')).toBeVisible({ timeout: 15_000 });
  }
);

Given(
  'Valeros joins {string} in a separate browser',
  async ({ browser, auth, world }, sessionTitle: string) => {
    const sessionIdMatch = sessionTitle.match(/\d+/);
    const sessionId = sessionIdMatch ? sessionIdMatch[0] : world.sessionId || '15';
    const campaignId = world.campaignId || '4';

    const valerosContext = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    world.extraContexts.push(valerosContext);
    const valerosPage = await valerosContext.newPage();
    world.setPage('valeros', valerosPage);

    await auth.injectUserIntoPage(valerosPage, 'valeros');
    await valerosPage.goto(`#/campaigns/${campaignId}/lobby/${sessionId}`);
    await valerosPage.waitForLoadState('domcontentloaded');
    await expect(valerosPage.locator('runefoble-session-lobby')).toBeVisible({ timeout: 15_000 });
  }
);

When('Valeros checks {string}', async ({ world }, controlLabel: string) => {
  const valerosPage = world.getPage('valeros') || world.getPage('evelyn')!;
  const lobby = valerosPage.locator('runefoble-session-lobby');

  if (controlLabel.toLowerCase().includes('ready')) {
    const readyCheckbox = lobby.locator('.checkbox-ready').first();
    await readyCheckbox.waitFor({ state: 'visible', timeout: 10_000 });
    await readyCheckbox.check();
  } else if (controlLabel.toLowerCase().includes('absent')) {
    const absentCheckbox = lobby.locator('.checkbox-absent').first();
    await absentCheckbox.waitFor({ state: 'visible', timeout: 10_000 });
    await absentCheckbox.check();
  }
});

Then(
  "Evelyn's lobby view updates in real time showing Valeros as {string}",
  async ({ world }, expectedStatus: string) => {
    const evelynPage = world.getPage('evelyn')!;
    const lobby = evelynPage.locator('runefoble-session-lobby');

    const valerosCard = lobby.locator('.participant-card').filter({ hasText: /Valeros/i }).first();
    await expect(valerosCard).toBeVisible({ timeout: 10_000 });

    const badge = valerosCard.locator('.badge-readiness');
    await expect(badge).toHaveText(expectedStatus, { timeout: 10_000 });
  }
);

When(
  'Sarah opens {string} and checks {string}',
  async ({ browser, auth, world }, sessionTitle: string, controlLabel: string) => {
    const sessionIdMatch = sessionTitle.match(/\d+/);
    const sessionId = sessionIdMatch ? sessionIdMatch[0] : world.sessionId || '15';
    const campaignId = world.campaignId || '4';

    const sarahContext = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    world.extraContexts.push(sarahContext);
    const sarahPage = await sarahContext.newPage();
    world.setPage('sarah', sarahPage);

    await auth.injectUserIntoPage(sarahPage, 'sarah');
    await sarahPage.goto(`#/campaigns/${campaignId}/lobby/${sessionId}`);
    await sarahPage.waitForLoadState('domcontentloaded');

    const lobby = sarahPage.locator('runefoble-session-lobby');
    await expect(lobby).toBeVisible({ timeout: 15_000 });

    if (controlLabel.toLowerCase().includes('absent')) {
      const sarahCard = lobby.locator('.participant-card').filter({ hasText: /Sarah/i }).first();
      const absentCheckbox = (await sarahCard.isVisible())
        ? sarahCard.locator('.checkbox-absent')
        : lobby.locator('.checkbox-absent').first();
      await absentCheckbox.waitFor({ state: 'visible', timeout: 10_000 });
      await absentCheckbox.check();
    }
  }
);

Then(
  'the participant card displays the {string} badge across all connected screens',
  async ({ world }, badgeName: string) => {
    const pages = [world.getPage('evelyn'), world.getPage('valeros'), world.getPage('sarah')].filter(Boolean) as Page[];

    for (const p of pages) {
      const badge = p
        .locator('runefoble-session-lobby .badge-readiness')
        .filter({ hasText: badgeName })
        .first();
      await expect(badge).toBeVisible({ timeout: 10_000 });
      await expect(badge).toHaveText(badgeName);
    }
  }
);

When('Evelyn clicks {string}', async ({ world }, buttonName: string) => {
  const evelynPage = world.getPage('evelyn')!;
  const btn = evelynPage
    .locator('runefoble-session-lobby button')
    .filter({ hasText: new RegExp(buttonName, 'i') })
    .first();
  await btn.waitFor({ state: 'visible', timeout: 10_000 });
  await btn.click();
});

Then(
  "both Evelyn and Valeros's browsers navigate automatically to {string}",
  async ({ world }, expectedHash: string) => {
    const evelynPage = world.getPage('evelyn')!;
    const valerosPage = world.getPage('valeros')!;

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
    const evelynPage = world.getPage('evelyn')!;
    const valerosPage = world.getPage('valeros')!;

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
    const valerosPage = world.getPage('valeros')!;
    const evelynPage = world.getPage('evelyn')!;

    // Launch through the DM's visible control. Valeros's browser follows the
    // session route on its own (see "both Evelyn and Valeros's browsers navigate").
    const evelynHash = await evelynPage.evaluate(() => window.location.hash);
    if (!evelynHash.includes('/sessions/')) {
      const launchBtn = evelynPage.locator('runefoble-session-lobby .btn-launch').first();
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

    const sourceCell = grid
      .locator('.cell')
      .filter({ has: valerosPage.locator('.coord-label', { hasText: `${fromX},${fromY}` }) })
      .first();
    const targetCell = grid
      .locator('.cell')
      .filter({ has: valerosPage.locator('.coord-label', { hasText: `${toX},${toY}` }) })
      .first();
    await expect(sourceCell).toBeVisible({ timeout: 10_000 });
    await expect(targetCell).toBeVisible({ timeout: 10_000 });

    const token = sourceCell.locator('.token').first();
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
    const evelynPage = world.getPage('evelyn')!;
    const board = evelynPage.locator('runefoble-board');
    await expect(board).toBeVisible({ timeout: 10_000 });

    const targetCell = board
      .locator('.cell')
      .filter({ has: evelynPage.locator('.coord-label', { hasText: `${toX},${toY}` }) })
      .first();

    await expect(targetCell.locator('.token')).toBeVisible({ timeout: 10_000 });
  }
);

Then('the chronicle feed logs the move action', async ({ world }) => {
  const evelynPage = world.getPage('evelyn')!;
  const watcherFeed = evelynPage.locator('runefoble-watcher-feed');
  await expect(watcherFeed).toBeVisible({ timeout: 10_000 });

  const moveEventItem = watcherFeed
    .locator('.event-item')
    .filter({ hasText: /moved to/i })
    .first();
  await expect(moveEventItem).toBeVisible({ timeout: 10_000 });
});
