/**
 * Unit & Integration tests for Character Roster Styles Modular Decomposition.
 * TASK-0222: Character Roster Styles Modular Decomposition
 * ADR-0004, ADR-0012
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

// Submodule imports
import {
  characterRosterStyles,
  rosterLayoutStyles,
  characterCardStyles,
  assignmentDialogStyles,
} from '../../services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts';

const REPO_ROOT = resolve(import.meta.dirname, '../../');

describe('Character Roster Styles: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies runefoble-character-roster.styles.ts is strictly < 50 lines (aggregator DoD 1)', () => {
    const filePath = resolve(
      REPO_ROOT,
      'services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts',
    );
    assert.ok(existsSync(filePath), 'Aggregator file must exist');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.trim().split('\n').length;
    assert.ok(lines < 50, `runefoble-character-roster.styles.ts has ${lines} lines, expected < 50`);
    assert.ok(lines < 40, `runefoble-character-roster.styles.ts has ${lines} lines, target < 40`);
  });

  it('verifies roster_layout.styles.ts is strictly < 130 lines (target < 110 lines)', () => {
    const filePath = resolve(
      REPO_ROOT,
      'services/character_sheet/ui/src/roster/styles/roster_layout.styles.ts',
    );
    assert.ok(existsSync(filePath), 'Layout styles file must exist');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.trim().split('\n').length;
    assert.ok(lines < 130, `roster_layout.styles.ts has ${lines} lines, strictly expected < 130`);
    assert.ok(lines < 110, `roster_layout.styles.ts has ${lines} lines, target < 110`);
  });

  it('verifies character_card.styles.ts is strictly < 130 lines (target < 120 lines)', () => {
    const filePath = resolve(
      REPO_ROOT,
      'services/character_sheet/ui/src/roster/styles/character_card.styles.ts',
    );
    assert.ok(existsSync(filePath), 'Character card styles file must exist');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.trim().split('\n').length;
    assert.ok(lines < 130, `character_card.styles.ts has ${lines} lines, strictly expected < 130`);
    assert.ok(lines < 120, `character_card.styles.ts has ${lines} lines, target < 120`);
  });

  it('verifies assignment_dialog.styles.ts is strictly < 130 lines (target < 120 lines)', () => {
    const filePath = resolve(
      REPO_ROOT,
      'services/character_sheet/ui/src/roster/styles/assignment_dialog.styles.ts',
    );
    assert.ok(existsSync(filePath), 'Assignment dialog styles file must exist');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.trim().split('\n').length;
    assert.ok(lines < 130, `assignment_dialog.styles.ts has ${lines} lines, strictly expected < 130`);
    assert.ok(lines < 120, `assignment_dialog.styles.ts has ${lines} lines, target < 120`);
  });
});

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

  it('verifies runefoble-character-roster component attaches characterRosterStyles', () => {
    const compPath = resolve(
      REPO_ROOT,
      'services/character_sheet/ui/src/roster/runefoble-character-roster.ts',
    );
    const compContent = readFileSync(compPath, 'utf-8');
    assert.ok(
      compContent.includes("static styles = [characterRosterStyles]"),
      'RunefobleCharacterRoster must attach characterRosterStyles',
    );
  });
});
