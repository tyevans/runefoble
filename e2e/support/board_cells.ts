/**
 * Board locators for the tactical board steps (TASK-0922).
 * Playwright CSS locators pierce the open Shadow DOM of `<runefoble-board>`.
 */

import type { Locator } from '@playwright/test';
import { exactText } from './guards';

/** The board cell whose coordinate label is exactly `x,y`. */
export function boardCell(board: Locator, x: number, y: number): Locator {
  return board
    .locator('.cell')
    .filter({ has: board.page().locator('.coord-label', { hasText: exactText(`${x},${y}`) }) });
}

/** The token of the character `name`. The token title starts with the character name. */
export function boardToken(board: Locator, name: string): Locator {
  return board.locator(`.token[title^="${name.replace(/"/g, '\\"')}"]`);
}
