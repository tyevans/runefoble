/**
 * Unit & Integration tests for Character Roster Styles Modular Decomposition.
 * TASK-0222: Character Roster Styles Modular Decomposition
 * ADR-0004, ADR-0012
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// Submodule imports
import {
  characterRosterStyles,
  rosterLayoutStyles,
  characterCardStyles,
  assignmentDialogStyles,
} from '../../services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts';

describe('Character Roster Styles: CSS Module Rules and Tokens Contract', () => {
  it('defines roster layout styles with host container, header, controls, and character grid', () => {
    assert.ok(rosterLayoutStyles);
    const cssText = rosterLayoutStyles.cssText;
    assert.ok(cssText.includes(':host'));
    assert.ok(cssText.includes('.roster-container'));
    assert.ok(cssText.includes('.roster-header'));
    assert.ok(cssText.includes('.title-group'));
    assert.ok(cssText.includes('.btn'));
    assert.ok(cssText.includes('.btn-primary'));
    assert.ok(cssText.includes('.btn-secondary'));
    assert.ok(cssText.includes('.btn-danger'));
    assert.ok(cssText.includes('.controls-bar'));
    assert.ok(cssText.includes('.search-input'));
    assert.ok(cssText.includes('.filter-pills'));
    assert.ok(cssText.includes('.filter-pill'));
    assert.ok(cssText.includes('.character-grid'));
    assert.ok(cssText.includes('--rf-font-family'));
    assert.ok(cssText.includes('--rf-text-primary'));
    assert.ok(cssText.includes('--rf-accent-primary'));
    assert.ok(cssText.includes('--rf-accent-secondary'));
  });

  it('defines character card styles with elevation, vitals badges, class tags, and token portrait', () => {
    assert.ok(characterCardStyles);
    const cssText = characterCardStyles.cssText;
    assert.ok(cssText.includes('.character-card'));
    assert.ok(cssText.includes('.card-top'));
    assert.ok(cssText.includes('.avatar-thumb'));
    assert.ok(cssText.includes('.card-identity'));
    assert.ok(cssText.includes('.card-name'));
    assert.ok(cssText.includes('.card-class'));
    assert.ok(cssText.includes('.card-level-badge'));
    assert.ok(cssText.includes('.vitals-row'));
    assert.ok(cssText.includes('.hp-header'));
    assert.ok(cssText.includes('.hp-bar-bg'));
    assert.ok(cssText.includes('.hp-bar-fill'));
    assert.ok(cssText.includes('.stats-row'));
    assert.ok(cssText.includes('.stat-chip'));
    assert.ok(cssText.includes('.campaign-badge'));
    assert.ok(cssText.includes('.card-actions'));
    assert.ok(cssText.includes('--rf-accent-tertiary'));
    assert.ok(cssText.includes('--rf-shadow'));
  });

  it('defines assignment dialog styles with modal backdrop, party controls, and empty roster state', () => {
    assert.ok(assignmentDialogStyles);
    const cssText = assignmentDialogStyles.cssText;
    assert.ok(cssText.includes('.empty-roster'));
    assert.ok(cssText.includes('.empty-icon'));
    assert.ok(cssText.includes('.modal-backdrop'));
    assert.ok(cssText.includes('.assign-dialog'));
    assert.ok(cssText.includes('.dialog-title'));
    assert.ok(cssText.includes('.dialog-select'));
    assert.ok(cssText.includes('.dialog-footer'));
    assert.ok(cssText.includes('--rf-z-modal'));
  });

  it('verifies aggregator characterRosterStyles contains all submodules in array', () => {
    assert.ok(Array.isArray(characterRosterStyles));
    const stylesArray = characterRosterStyles as unknown[];
    assert.strictEqual(stylesArray.length, 3);
    assert.ok(stylesArray.includes(rosterLayoutStyles));
    assert.ok(stylesArray.includes(characterCardStyles));
    assert.ok(stylesArray.includes(assignmentDialogStyles));
  });

});
