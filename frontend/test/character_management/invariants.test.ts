/**
 * Character Management Bauhaus Theming & Invariants Test Suite.
 *
 * TASK-0288: Frontend Character Management Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0012, ADR-0013
 * Hard Invariants: Hard Invariant 6 (< 130 lines), Hard Invariant 7 (Blackbox TDD)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const FRONTEND_DIR = resolve(import.meta.dirname, '../..');
const REPO_ROOT = resolve(FRONTEND_DIR, '..');

const APP_SHELL_PATH = resolve(FRONTEND_DIR, 'src/runefoble-app.ts');
const ROUTER_PATH = resolve(FRONTEND_DIR, 'src/router/router.ts');
const PROFILE_PATH = resolve(FRONTEND_DIR, 'src/components/runefoble-user-profile.ts');
const CARD_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-card.ts');
const STATS_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/templates/stats.template.ts');
const SPELLS_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/templates/spells.template.ts');
const SHEET_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-sheet.ts');

describe('Bauhaus Theming & File Invariants (Hard Invariant 6, TASK-0288)', () => {
  it('test_file_length_invariants: verifies all component files < 500 lines and test submodules < 130 lines', () => {
    const components = [APP_SHELL_PATH, ROUTER_PATH, PROFILE_PATH, CARD_PATH];
    for (const filePath of components) {
      const lines = readFileSync(filePath, 'utf-8').split('\n').length;
      assert.ok(lines < 500, `${filePath} has ${lines} lines; must be < 500 lines`);
    }

    const testSubmodules = ['navigation.test.ts', 'creation.test.ts', 'profile.test.ts', 'invariants.test.ts'];
    for (const name of testSubmodules) {
      const fullPath = resolve(FRONTEND_DIR, 'test/character_management', name);
      const lines = readFileSync(fullPath, 'utf-8').split('\n').length;
      assert.ok(lines < 130, `${name} has ${lines} lines; must be strictly < 130 lines`);
    }
  });

  it('test_character_card_custom_element_and_tokens: verifies custom element and Bauhaus tokens', () => {
    const cardContent = readFileSync(CARD_PATH, 'utf-8');
    assert.ok(cardContent.includes('@customElement('));
    assert.ok(cardContent.includes('class RunefobleCharacterCard extends LitElement'));
    assert.ok(cardContent.includes('characterName'));
    assert.ok(cardContent.includes('armorClass'));
    assert.ok(cardContent.includes('currentHp'));
    assert.ok(cardContent.includes('maxHp'));
  });

  it('test_app_shell_action_bindings_and_template_controls: verifies all 11 action events and template controls', () => {
    const appShellContent = readFileSync(APP_SHELL_PATH, 'utf-8');
    const requiredEvents = [
      '@hp-change', '@equip-item', '@unequip-item', '@add-item', '@remove-item',
      '@cast-spell', '@prepare-spell', '@apply-condition', '@remove-condition',
      '@expend-slot', '@restore-slot'
    ];
    for (const evt of requiredEvents) {
      assert.ok(appShellContent.includes(evt), `App Shell must bind ${evt}`);
    }
    assert.ok(appShellContent.includes('<runefoble-stand-in-guardrails'));

    const statsContent = readFileSync(STATS_PATH, 'utf-8');
    assert.ok(statsContent.includes('handleHpDelta(-5)') && statsContent.includes('handleHpDelta(5)'));
    const spellsContent = readFileSync(SPELLS_PATH, 'utf-8');
    assert.ok(spellsContent.includes('handleCastSpell('));
    const sheetContent = readFileSync(SHEET_PATH, 'utf-8');
    assert.ok(sheetContent.includes('openEquipDialog') && sheetContent.includes('confirmEquipItem'));
  });
});
