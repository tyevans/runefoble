/**
 * Unit & Integration tests for Stand-In Guardrails Decomposition.
 * TASK-0203: Stand-In Guardrails Microfrontend Styles and Controls Modular Decomposition
 * ADR-0004, ADR-0012, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Submodule imports
import { standInGuardrailsStyles } from '../../services/character_sheet/ui/src/runefoble-stand-in-guardrails.styles.ts';
import {
  renderHeader,
  renderSpellSlotPreservation,
  renderSliderControls,
  renderAllyProtectionTags,
  renderPostureSelector,
  renderCustomPriorityChips,
  renderActionsBar,
} from '../../services/character_sheet/ui/src/runefoble-stand-in-guardrails.templates.ts';

const REPO_ROOT = resolve(import.meta.dirname, '../../');

describe('Stand-In Guardrails: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies runefoble-stand-in-guardrails.ts is strictly < 130 lines', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 130, `runefoble-stand-in-guardrails.ts has ${lines} lines, expected < 130`);
  });

  it('verifies runefoble-stand-in-guardrails.styles.ts is strictly < 130 lines', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-stand-in-guardrails.styles.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 130, `runefoble-stand-in-guardrails.styles.ts has ${lines} lines, expected < 130`);
  });

  it('verifies runefoble-stand-in-guardrails.templates.ts is strictly < 130 lines', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-stand-in-guardrails.templates.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 130, `runefoble-stand-in-guardrails.templates.ts has ${lines} lines, expected < 130`);
  });
});

describe('Stand-In Guardrails: Styles Submodule Contract', () => {
  it('defines standInGuardrailsStyles with Bauhaus design tokens', () => {
    assert.ok(standInGuardrailsStyles);
    const cssText = standInGuardrailsStyles.cssText;
    assert.ok(cssText.includes('--rf-bg-card'));
    assert.ok(cssText.includes('--rf-border-color'));
    assert.ok(cssText.includes('--rf-accent-secondary'));
    assert.ok(cssText.includes('--rf-accent-tertiary'));
  });
});

describe('Stand-In Guardrails: Templates Submodule Contract', () => {
  const dummyHost = {
    characterId: 'char-123',
    characterName: 'Kyra',
    preserveSpellSlots: { 3: 1 },
    protectAllies: ['Marcus', 'Valeros'],
    protectAllyHpThreshold: 0.3,
    riskThreshold: 'cautious' as const,
    avoidMelee: true,
    permadeathSafeguard: true,
    customPriorities: ['Save Level 3 slots for Revivify'],
    newAllyInput: '',
    newPriorityInput: '',
    saveStatus: 'Saved!',
    handleHotSwap: () => {},
    handleSave: () => {},
    addAlly: () => {},
    removeAlly: (_i: number) => {},
    addPriority: () => {},
    removePriority: (_i: number) => {},
  } as any;

  it('renders header template with character name and hot-swap button', () => {
    const result = renderHeader(dummyHost);
    assert.ok(result);
    assert.ok(result.strings.some((s: string) => s.includes('Stand-In Tactical Guardrails')));
    assert.ok(result.values.some((v: unknown) => String(v).includes('Kyra')));
  });

  it('renders spell slot preservation toggle', () => {
    const result = renderSpellSlotPreservation(dummyHost);
    assert.ok(result);
    assert.ok(result.strings.some((s: string) => s.includes('Reserve Level 3 Slots')));
  });

  it('renders slider controls for protection HP threshold', () => {
    const result = renderSliderControls(dummyHost);
    assert.ok(result);
    assert.ok(result.values.some((v: unknown) => v === 30));
  });

  it('renders ally protection tags and input', () => {
    const result = renderAllyProtectionTags(dummyHost);
    assert.ok(result);
    assert.ok(result.strings.some((s: string) => s.includes('Party Member Protection Affinities')));
  });

  it('renders posture selector and risk toggles', () => {
    const result = renderPostureSelector(dummyHost);
    assert.ok(result);
    assert.ok(result.strings.some((s: string) => s.includes('Tactical Posture & Risk Thresholds')));
  });

  it('renders custom priority chips and input', () => {
    const result = renderCustomPriorityChips(dummyHost);
    assert.ok(result);
    assert.ok(result.strings.some((s: string) => s.includes('Custom Tactical Priorities')));
  });

  it('renders actions bar with save button and status message', () => {
    const result = renderActionsBar(dummyHost);
    assert.ok(result);
    assert.ok(result.values.some((v: unknown) => v === 'Saved!'));
  });
});

describe('Stand-In Guardrails: Component Controller Contract', () => {
  it('verifies runefoble-stand-in-guardrails.ts exports RunefobleStandInGuardrails custom element and imports styles & templates', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts');
    const content = readFileSync(filePath, 'utf-8');
    assert.ok(content.includes("@customElement('runefoble-stand-in-guardrails')"));
    assert.ok(content.includes('export class RunefobleStandInGuardrails'));
    assert.ok(content.includes('standInGuardrailsStyles'));
    assert.ok(content.includes('renderActionsBar'));
    assert.ok(content.includes('renderAllyProtectionTags'));
    assert.ok(content.includes('renderCustomPriorityChips'));
    assert.ok(content.includes('renderHeader'));
    assert.ok(content.includes('renderPostureSelector'));
    assert.ok(content.includes('renderSpellSlotPreservation'));
    assert.ok(content.includes("'runefoble-stand-in-guardrails': RunefobleStandInGuardrails"));
  });
});
