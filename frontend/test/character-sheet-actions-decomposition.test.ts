/**
 * Unit & Integration tests for Character Sheet Actions Decomposition.
 * TASK-0204: Character Sheet Component Action Handlers and State Modular Decomposition
 * ADR-0004, ADR-0007, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Submodule imports
import {
  addItem,
  applyConditionToState,
  calculateEncumbrance,
  calculateHpDelta,
  castSpellSlot,
  dispatchActionEvent,
  equipItem,
  removeConditionFromState,
  removeItem,
  syncCharacterResponse,
  togglePreparedSpell,
  toggleSpellSlotPip,
  unequipItem,
} from '../../services/character_sheet/ui/src/runefoble-character-sheet.actions.ts';
import type { InventoryItem } from '../../services/character_sheet/ui/src/runefoble-character-sheet.types.ts';

const REPO_ROOT = resolve(import.meta.dirname, '../../');

describe('Character Sheet: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies runefoble-character-sheet.ts is strictly < 150 lines', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-sheet.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 150, `runefoble-character-sheet.ts has ${lines} lines, expected < 150`);
  });

  it('verifies runefoble-character-sheet.actions.ts is strictly < 130 lines', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-sheet.actions.ts');
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    assert.ok(lines < 130, `runefoble-character-sheet.actions.ts has ${lines} lines, expected < 130`);
  });
});

describe('Character Sheet: Actions Submodule State Mutations & Calculations', () => {
  it('calculates encumbrance tiers and percentages accurately', () => {
    const items: InventoryItem[] = [
      { item_id: '1', name: 'Plate Armor', quantity: 1, weight_lbs: 65 },
      { item_id: '2', name: 'Greatsword', quantity: 1, weight_lbs: 6 },
    ];
    const enc = calculateEncumbrance(items, 10);
    assert.equal(enc.totalWeight, 71);
    assert.equal(enc.maxCapacity, 100);
    assert.equal(enc.tier, 'heavy');
    assert.equal(enc.percentage, 71);

    const heavyItems: InventoryItem[] = [
      { item_id: '1', name: 'Boulders', quantity: 2, weight_lbs: 60 },
    ];
    const overburdened = calculateEncumbrance(heavyItems, 10);
    assert.equal(overburdened.tier, 'overburdened');
  });

  it('calculates HP deltas with boundaries', () => {
    assert.equal(calculateHpDelta(30, 40, -15), 15);
    assert.equal(calculateHpDelta(10, 40, -25), 0);
    assert.equal(calculateHpDelta(35, 40, 10), 40);
  });

  it('handles item equipping and unequipping', () => {
    const equipment = { main_hand: null };
    const inventory: InventoryItem[] = [
      { item_id: 'item-1', name: 'Shortsword', quantity: 1, weight_lbs: 2.0 },
    ];

    const equipped = equipItem(equipment, inventory, 'main_hand', inventory[0]);
    assert.equal(equipped.equipment.main_hand, 'Shortsword');
    assert.equal(equipped.inventory[0].slot, 'main_hand');

    const unequipped = unequipItem(equipped.equipment, equipped.inventory, 'main_hand');
    assert.equal(unequipped.equipment.main_hand, undefined);
    assert.equal(unequipped.inventory[0].slot, undefined);
    assert.equal(unequipped.unequippedName, 'Shortsword');
  });

  it('handles adding and removing items with quantity and slot checks', () => {
    let inventory: InventoryItem[] = [];
    const added = addItem(inventory, 'Rope (50ft)', 10.0);
    assert.equal(added.inventory.length, 1);
    assert.equal(added.addedItem?.name, 'Rope (50ft)');

    // Stacking quantity decrement
    const multiItem: InventoryItem = { item_id: 'pot', name: 'Potion', quantity: 2, weight_lbs: 0.5 };
    const dec = removeItem({}, [multiItem], multiItem);
    assert.equal(dec.inventory[0].quantity, 1);

    // Full removal & unequip
    const singleItem: InventoryItem = { item_id: 'sword', name: 'Sword', quantity: 1, weight_lbs: 3.0 };
    const eq = { main_hand: 'Sword' };
    const rem = removeItem(eq, [singleItem], singleItem);
    assert.equal(rem.inventory.length, 0);
    assert.equal(rem.equipment.main_hand, undefined);
  });

  it('toggles spell slot pips between expend and restore', () => {
    const slots = { 1: 3 };
    const maxSlots = { 1: 4 };

    // Click available pip (expend)
    const expended = toggleSpellSlotPip(slots, maxSlots, 1, 1);
    assert.equal(expended.remaining, 2);
    assert.equal(expended.action, 'expend-slot');

    // Click expended pip (restore)
    const restored = toggleSpellSlotPip(slots, maxSlots, 1, 3);
    assert.equal(restored.remaining, 4);
    assert.equal(restored.action, 'restore-slot');
  });

  it('casts spell and consumes available slot', () => {
    const slots = { 1: 2 };
    const cast = castSpellSlot(slots, 1);
    assert.equal(cast.remaining, 1);
    assert.equal(cast.slots[1], 1);
  });

  it('toggles spell preparation status', () => {
    const prepared = ['Magic Missile'];
    const toggledOn = togglePreparedSpell(prepared, 'Shield');
    assert.ok(toggledOn.isPrepared);
    assert.deepEqual(toggledOn.preparedSpells, ['Magic Missile', 'Shield']);

    const toggledOff = togglePreparedSpell(toggledOn.preparedSpells, 'Magic Missile');
    assert.ok(!toggledOff.isPrepared);
    assert.deepEqual(toggledOff.preparedSpells, ['Shield']);
  });

  it('applies tactical conditions and absence penalties to state', () => {
    const res = applyConditionToState([], 'blinded');
    assert.equal(res.conditions.length, 1);
    assert.equal(res.newCondition.name, 'blinded');
    assert.equal(res.newCondition.source, 'tactical');

    const penRes = applyConditionToState([], 'drunk');
    assert.equal(penRes.newCondition.source, 'session_penalty');
  });

  it('removes conditions and clears associated absence penalties', () => {
    const cond = { id: 'c-1', name: 'drunk', source: 'session_penalty', description: 'Drunk' };
    const penalties = { drunk: 'Missed session' };
    const cleaned = removeConditionFromState([cond], penalties, 'c-1', 'drunk');
    assert.equal(cleaned.conditions.length, 0);
    assert.equal(cleaned.penalties.drunk, undefined);
  });

  it('syncs fetched character response payload to host', () => {
    const host: any = { requestUpdate: () => {} };
    syncCharacterResponse(host, {
      name: 'Golarion Ranger',
      character_class: 'Ranger 3',
      level: 3,
      current_hp: 28,
      max_hp: 28,
      is_stand_in_active: true,
      equipment: { main_hand: 'Longbow' },
    });
    assert.equal(host.characterName, 'Golarion Ranger');
    assert.equal(host.characterClass, 'Ranger 3');
    assert.equal(host.level, 3);
    assert.equal(host.isAiStandIn, true);
    assert.equal(host.equipment.main_hand, 'Longbow');
  });

  it('dispatches custom event with proper bubbling and composed options', () => {
    let receivedEvent: CustomEvent | null = null;
    const target = new EventTarget();
    target.addEventListener('test-action', ((e: CustomEvent) => {
      receivedEvent = e;
    }) as EventListener);

    dispatchActionEvent(target, 'test-action', { status: 'success' });
    assert.ok(receivedEvent);
    assert.equal((receivedEvent as CustomEvent).bubbles, true);
    assert.equal((receivedEvent as CustomEvent).composed, true);
    assert.deepEqual((receivedEvent as CustomEvent).detail, { status: 'success' });
  });
});

describe('Character Sheet: Component Controller Contract', () => {
  it('verifies runefoble-character-sheet.ts exports RunefobleCharacterSheet custom element and delegates action handlers', () => {
    const filePath = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-sheet.ts');
    const content = readFileSync(filePath, 'utf-8');
    assert.ok(content.includes("@customElement('runefoble-character-sheet')"));
    assert.ok(content.includes('export class RunefobleCharacterSheet'));
    assert.ok(content.includes('runefoble-character-sheet.actions.ts'));
    assert.ok(content.includes('handleEquipItem('));
    assert.ok(content.includes('handleUnequipItem('));
    assert.ok(content.includes('handleAddItem('));
    assert.ok(content.includes('handleRemoveItem('));
    assert.ok(content.includes('handleHpDelta('));
    assert.ok(content.includes('handlePipClick('));
    assert.ok(content.includes('handleCastSpell('));
    assert.ok(content.includes('handleTogglePrepare('));
    assert.ok(content.includes('handleApplyCondition('));
    assert.ok(content.includes('handleRemoveCondition('));
    assert.ok(content.includes("'runefoble-character-sheet': RunefobleCharacterSheet"));
  });
});
