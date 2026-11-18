/**
 * Unit & Integration tests for Settlement Bulletin Board Styles Decomposition.
 * TASK-0274: Settlement Bulletin Board Styles Modular Decomposition
 * ADR-0004, ADR-0012
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// Submodule imports
import {
  bulletinBoardStyles,
  bulletinBoardLayoutStyles,
  bulletinBoardCardStyles,
  bulletinBoardDialogStyles,
} from '../src/components/runefoble-bulletin-board.styles.ts';

describe('Bulletin Board Styles: CSS Module Rules and Tokens Contract', () => {
  it('defines layout styles with corkboard grid and controls rules', () => {
    assert.ok(bulletinBoardLayoutStyles);
    const cssText = bulletinBoardLayoutStyles.cssText;
    assert.ok(cssText.includes('.bulletin-board-container'));
    assert.ok(cssText.includes('.board-header'));
    assert.ok(cssText.includes('.board-controls'));
    assert.ok(cssText.includes('.cards-grid'));
    assert.ok(cssText.includes('.empty-board-state'));
    assert.ok(cssText.includes('--rf-text-primary'));
    assert.ok(cssText.includes('--rf-accent-primary'));
  });

  it('defines card styles with parchment, wax seal, and cipher indicator', () => {
    assert.ok(bulletinBoardCardStyles);
    const cssText = bulletinBoardCardStyles.cssText;
    assert.ok(cssText.includes('.notice-card'));
    assert.ok(cssText.includes('.push-pin'));
    assert.ok(cssText.includes('.wax-seal-badge'));
    assert.ok(cssText.includes('.cipher-indicator'));
    assert.ok(cssText.includes('.category-badge'));
    assert.ok(cssText.includes('--rf-bg-card'));
    assert.ok(cssText.includes('--rf-border-subtle'));
  });

  it('defines dialog styles with parchment modal, cipher puzzle, and actions', () => {
    assert.ok(bulletinBoardDialogStyles);
    const cssText = bulletinBoardDialogStyles.cssText;
    assert.ok(cssText.includes('.modal-backdrop'));
    assert.ok(cssText.includes('.parchment-modal'));
    assert.ok(cssText.includes('.cipher-mini-puzzle'));
    assert.ok(cssText.includes('.modal-actions'));
    assert.ok(cssText.includes('.danger-btn'));
    assert.ok(cssText.includes('.secondary-btn'));
  });

  it('verifies aggregator bulletinBoardStyles contains all submodules in array', () => {
    assert.ok(Array.isArray(bulletinBoardStyles));
    const stylesArray = bulletinBoardStyles as unknown[];
    assert.strictEqual(stylesArray.length, 3);
    assert.ok(stylesArray.includes(bulletinBoardLayoutStyles));
    assert.ok(stylesArray.includes(bulletinBoardCardStyles));
    assert.ok(stylesArray.includes(bulletinBoardDialogStyles));
  });
});
