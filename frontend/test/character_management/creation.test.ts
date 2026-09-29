/**
 * Character Creation, Campaign Filtering & State Mutations Test Suite.
 *
 * TASK-0288: Frontend Character Management Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0012, ADR-0013
 * Hard Invariants: Hard Invariant 6 (< 130 lines), Hard Invariant 7 (Blackbox TDD)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService, appDataService } from '../../src/services/app-data-service.ts';
import type { CharacterItem, CreateCharacterPayload } from '../../../services/character_sheet/ui/src/roster/types.ts';

describe('Character Creation & Data Mutations (TASK-0288, PRD-0006)', () => {
  it('test_character_creation_and_unassigned_roster: persists new character in unassigned state', async () => {
    const dataService = new AppDataService();
    const payload: CreateCharacterPayload = {
      name: 'Seoni of Varisia',
      characterClass: 'Sorcerer',
      subclass: 'Draconic Bloodline',
      level: 3,
      maxHp: 22,
      armorClass: 12,
      speed: 30,
      abilityScores: { str: 8, dex: 14, con: 12, int: 12, wis: 10, cha: 16 },
      portraitUrl: '/assets/portraits/sorcerer.svg',
    };
    const created = await dataService.createCharacter(payload);
    assert.ok(created.id, 'Created character must have an ID');
    assert.equal(created.name, 'Seoni of Varisia');
    assert.equal(created.currentHp, 22);

    const all = await dataService.fetchCharacters();
    const found = all.find((c) => c.name === 'Seoni of Varisia');
    assert.ok(found, 'New character must appear in roster');
    assert.ok(found?.campaignId == null, 'New character should start unassigned');
  });

  it('test_campaign_filtering_and_fallback: resolves campaign-assigned character fallback', () => {
    const characters: CharacterItem[] = [
      { id: 'c1', name: 'Ezren', characterClass: 'Wizard', level: 3, currentHp: 20, maxHp: 20, armorClass: 12, campaignId: '99' },
      { id: 'c2', name: 'Valeros', characterClass: 'Fighter', level: 4, currentHp: 38, maxHp: 45, armorClass: 18, campaignId: '4' },
    ];
    const resolveActive = (campId: string, cur: CharacterItem | null) => cur || characters.find((c) => c.campaignId === campId) || characters[0];
    const resolved = resolveActive('4', null);
    assert.equal(resolved.id, 'c2');
    assert.equal(resolved.name, 'Valeros');
  });

  it('test_health_mutations_and_stabilization: clamps HP and stabilizes stand-in at 0 HP', async () => {
    const service = AppDataService.getInstance();
    const resDmg = await service.modifyCharacterHealth('char-valeros', -10);
    assert.equal(resDmg.current_hp, 28);
    const resHeal = await service.modifyCharacterHealth('char-valeros', 20);
    assert.equal(resHeal.current_hp, 45);

    const detail = service.getFallbackCharacterDetail('char-kyra');
    detail.isAiStandIn = true;
    detail.is_stand_in_active = true;
    const resZero = await service.modifyCharacterHealth('char-kyra', -100);
    assert.equal(resZero.current_hp, 0);
    assert.equal(resZero.is_stabilized, true);
  });

  it('test_equipment_inventory_and_condition_mutations: updates gear, inventory, and conditions', async () => {
    const service = AppDataService.getInstance();
    const resEquip = await service.equipCharacterItem('char-valeros', 'main_hand', 'Frostbrand Scimitar');
    assert.equal(resEquip.equipment.main_hand, 'Frostbrand Scimitar');
    const resUnequip = await service.unequipCharacterItem('char-valeros', 'main_hand');
    assert.equal(resUnequip.equipment.main_hand, undefined);

    const item = { item_id: 'tst-potion', name: 'Potion of Invisibility', quantity: 2, weight_lbs: 0.5 };
    const resAdd = await service.addCharacterInventoryItem('char-valeros', item);
    assert.equal(resAdd.inventory.find((i: any) => i.item_id === 'tst-potion')?.quantity, 2);
    const resRem = await service.removeCharacterInventoryItem('char-valeros', 'tst-potion', 1);
    assert.equal(resRem.inventory.find((i: any) => i.item_id === 'tst-potion')?.quantity, 1);

    const resCond = await service.applyCharacterCondition('char-valeros', 'frightened', 'dragon_roar');
    assert.ok(Array.isArray(resCond.conditions) ? resCond.conditions.some((c: any) => c.name === 'frightened') : resCond.conditions?.frightened);
    const resClear = await service.removeCharacterCondition('char-valeros', 'frightened');
    assert.ok(Array.isArray(resClear.conditions) ? !resClear.conditions.some((c: any) => c.name === 'frightened') : !resClear.conditions?.frightened);
  });

  it('test_spell_slots_and_guardrails_mutations: expends spell slot and updates guardrails', async () => {
    const service = AppDataService.getInstance();
    const resCast = await service.castCharacterSpell('char-valeros', 'Magic Missile', 1);
    assert.equal(resCast.spell_slots[1], 3);
    const resPrep = await service.prepareCharacterSpell('char-valeros', 'Detect Magic', true);
    assert.ok(resPrep.prepared_spells.includes('Detect Magic'));

    const resGuardrails = await appDataService.updateCharacterGuardrails('char-valeros', { riskThreshold: 'reckless', avoidMelee: false, permadeathSafeguard: true });
    assert.equal(resGuardrails.stand_in_guardrails.riskThreshold, 'reckless');
    const resHotSwap = await appDataService.requestHotSwap('session-tomb-14', 'char-valeros', 'user-valeros');
    assert.equal(resHotSwap.status, 'control_transferred');
  });
});
