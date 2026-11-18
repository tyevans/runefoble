/**
 * Character Sub-Resource Mutations Test Suite.
 *
 * TASK-0288: Frontend Character Management Test Suite Modular Decomposition
 * TASK-0640: Mutations are checked at the fetch boundary and return typed results.
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0014
 * Hard Invariants: Hard Invariant 6 (< 130 lines), Hard Invariant 7 (Blackbox TDD)
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService, appDataService } from '../../src/services/app-data-service.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';

const VALEROS_SHEET = { id: 'char-valeros', name: 'Valeros of Korvosa', equipment: {}, inventory: [], conditions: {}, spell_slots: { 1: 4 }, prepared_spells: ['Shield'] };

describe('Character Sub-Resource Mutations (TASK-0288, TASK-0640)', () => {
  let gateway: FakeGateway | undefined;

  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('test_health_mutations_and_stabilization: forwards health deltas and returns the gateway sheet', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/characters/char-valeros/health': (req) => {
        const delta = (req.body as any).delta;
        return { body: { ...VALEROS_SHEET, current_hp: Math.min(45, Math.max(0, 38 + delta)) } };
      },
      'POST /api/v1/characters/char-kyra/health': { body: { id: 'char-kyra', current_hp: 0, is_stabilized: true } },
    });
    const service = AppDataService.getInstance();
    const resDmg = await service.modifyCharacterHealth('char-valeros', -10);
    assert.ok(resDmg.ok);
    assert.equal(resDmg.data.current_hp, 28);
    const resHeal = await service.modifyCharacterHealth('char-valeros', 20);
    assert.ok(resHeal.ok);
    assert.equal(resHeal.data.current_hp, 45);

    const resZero = await service.modifyCharacterHealth('char-kyra', -100);
    assert.ok(resZero.ok);
    assert.equal(resZero.data.current_hp, 0);
    assert.equal(resZero.data.is_stabilized, true);
  });

  it('test_health_mutation_rejected_reports_error_and_no_hp: a rejected health change is an error result', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/characters/char-valeros/health': { status: 409, body: { detail: 'Character is locked by an active session' } },
    });
    const result = await AppDataService.getInstance().modifyCharacterHealth('char-valeros', -10);
    assert.equal(result.ok, false);
    assert.equal('data' in result, false);
    assert.equal(result.ok === false && result.message, 'Character is locked by an active session');
  });

  it('test_equipment_inventory_and_condition_mutations: updates gear, inventory, and conditions', async () => {
    const calls: string[] = [];
    gateway = installFakeGateway({
      'POST /api/v1/characters/char-valeros/equipment': (req) => {
        calls.push('equip');
        return { body: { equipment: { [(req.body as any).slot]: (req.body as any).item_name } } };
      },
      'DELETE /api/v1/characters/char-valeros/equipment/main_hand': () => { calls.push('unequip'); return { body: { equipment: {} } }; },
      'POST /api/v1/characters/char-valeros/inventory': () => { calls.push('add'); return { body: { inventory: [{ item_id: 'tst-potion', quantity: 2 }] } }; },
      'DELETE /api/v1/characters/char-valeros/inventory/tst-potion': () => { calls.push('remove'); return { body: { inventory: [{ item_id: 'tst-potion', quantity: 1 }] } }; },
      'POST /api/v1/characters/char-valeros/conditions': () => { calls.push('apply'); return { body: { conditions: [{ name: 'frightened' }] } }; },
      'DELETE /api/v1/characters/char-valeros/conditions/frightened': () => { calls.push('clear'); return { body: { conditions: [] } }; },
    });
    const service = AppDataService.getInstance();
    const resEquip = await service.equipCharacterItem('char-valeros', 'main_hand', 'Frostbrand Scimitar');
    assert.ok(resEquip.ok);
    assert.equal(resEquip.data.equipment.main_hand, 'Frostbrand Scimitar');
    const resUnequip = await service.unequipCharacterItem('char-valeros', 'main_hand');
    assert.ok(resUnequip.ok);
    assert.equal(resUnequip.data.equipment.main_hand, undefined);

    const item = { item_id: 'tst-potion', name: 'Potion of Invisibility', quantity: 2, weight_lbs: 0.5 };
    const resAdd = await service.addCharacterInventoryItem('char-valeros', item);
    assert.ok(resAdd.ok);
    assert.equal(resAdd.data.inventory.find((i: any) => i.item_id === 'tst-potion')?.quantity, 2);
    const resRem = await service.removeCharacterInventoryItem('char-valeros', 'tst-potion', 1);
    assert.ok(resRem.ok);
    assert.equal(resRem.data.inventory.find((i: any) => i.item_id === 'tst-potion')?.quantity, 1);

    const resCond = await service.applyCharacterCondition('char-valeros', 'frightened', 'dragon_roar');
    assert.ok(resCond.ok);
    assert.ok(resCond.data.conditions.some((c: any) => c.name === 'frightened'));
    const resClear = await service.removeCharacterCondition('char-valeros', 'frightened');
    assert.ok(resClear.ok);
    assert.equal(resClear.data.conditions.some((c: any) => c.name === 'frightened'), false);
    assert.deepEqual(calls, ['equip', 'unequip', 'add', 'remove', 'apply', 'clear']);
  });

  it('test_spell_slots_and_guardrails_mutations: expends spell slot and updates guardrails', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/characters/char-valeros/spells/cast': { body: { ...VALEROS_SHEET, spell_slots: { 1: 3 } } },
      'POST /api/v1/characters/char-valeros/spells/prepare': { body: { ...VALEROS_SHEET, prepared_spells: ['Shield', 'Detect Magic'] } },
      'PUT /api/v1/characters/char-valeros/guardrails': (req) => ({ body: { stand_in_guardrails: req.body } }),
      'POST /api/v1/sessions/session-tomb-14/hot-swap': { body: { status: 'control_transferred' } },
    });
    const service = AppDataService.getInstance();
    const resCast = await service.castCharacterSpell('char-valeros', 'Magic Missile', 1);
    assert.ok(resCast.ok);
    assert.equal(resCast.data.spell_slots[1], 3);
    const resPrep = await service.prepareCharacterSpell('char-valeros', 'Detect Magic', true);
    assert.ok(resPrep.ok);
    assert.ok(resPrep.data.prepared_spells.includes('Detect Magic'));

    const resGuardrails = await service.updateCharacterGuardrails('char-valeros', { riskThreshold: 'reckless', avoidMelee: false, permadeathSafeguard: true });
    assert.ok(resGuardrails.ok);
    assert.equal(resGuardrails.data.stand_in_guardrails.riskThreshold, 'reckless');
    const resHotSwap = await service.requestHotSwap('session-tomb-14', 'char-valeros', 'user-fixture');
    assert.ok(resHotSwap.ok);
    assert.equal(resHotSwap.data.status, 'control_transferred');
  });
});
