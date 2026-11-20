/**
 * Character sheet handlers change view state with new objects (TASK-0908).
 *
 * Lit renders a child again only when a property gets a new reference. After a confirmed
 * write, each handler must put a new character object on the host. After a refused write,
 * the handler must keep the old object and show the error, never a success message.
 * The gateway is faked at the fetch boundary. Governing ADRs: ADR-0004, ADR-0015.
 */

import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import {
  handleGuardrailsSaved,
  handleHotSwapRequested,
  handleSheetApplyCondition,
  handleSheetCastSpell,
  handleSheetEquipItem,
  handleSheetPrepareSpell,
} from '../../src/character-sheet-handlers.ts';

interface Host { selectedCharacter: any; characters: any[]; activeCharacter: any; sessionId: string; toasts: string[]; showToast(m: string): void }

function makeHost(): Host {
  const sheet = { id: 'char-1', name: 'Valeros', equipment: {}, conditions: [], spell_slots: { 1: 2 }, prepared_spells: ['Shield'] };
  return {
    selectedCharacter: sheet,
    characters: [sheet],
    activeCharacter: null,
    sessionId: 'session-1',
    toasts: [],
    showToast(m: string) { this.toasts.push(m); },
  };
}

const event = (detail: unknown) => ({ detail }) as CustomEvent;

describe('character sheet handlers replace the character object', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('equip puts a new character and a new equipment object on the host', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/characters/char-1/equipment': { body: {} } });
    const host = makeHost();
    const before = host.selectedCharacter;

    await handleSheetEquipItem(host, 'char-1', event({ slot: 'main_hand', itemName: 'Longsword' }));

    assert.notEqual(host.selectedCharacter, before);
    assert.notEqual(host.selectedCharacter.equipment, before.equipment);
    assert.equal(host.selectedCharacter.equipment.main_hand, 'Longsword');
    assert.deepEqual(before.equipment, {});
  });

  it('cast, prepare and apply-condition replace the nested objects', async () => {
    gateway = installFakeGateway({ '*': { body: {} } });
    const host = makeHost();
    const before = host.selectedCharacter;

    await handleSheetCastSpell(host, 'char-1', event({ spellName: 'Magic Missile', slotLevel: 1 }));
    assert.notEqual(host.selectedCharacter.spell_slots, before.spell_slots);
    assert.equal(host.selectedCharacter.spell_slots[1], 1);

    const beforePrepare = host.selectedCharacter;
    await handleSheetPrepareSpell(host, 'char-1', event({ spellName: 'Detect Magic', prepared: true }));
    assert.notEqual(host.selectedCharacter.prepared_spells, beforePrepare.prepared_spells);
    assert.deepEqual(host.selectedCharacter.prepared_spells, ['Shield', 'Detect Magic']);

    const beforeCondition = host.selectedCharacter;
    await handleSheetApplyCondition(host, 'char-1', event({ condition: 'frightened', source: 'dragon' }));
    assert.notEqual(host.selectedCharacter.conditions, beforeCondition.conditions);
    assert.equal(host.selectedCharacter.conditions.length, 1);
    assert.deepEqual(before.spell_slots, { 1: 2 });
    assert.deepEqual(before.prepared_spells, ['Shield']);
  });

  it('a refused equip keeps the old character and shows the server message', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/characters/char-1/equipment': { status: 409, body: { detail: 'Sheet is locked' } } });
    const host = makeHost();
    const before = host.selectedCharacter;

    await handleSheetEquipItem(host, 'char-1', event({ slot: 'main_hand', itemName: 'Longsword' }));

    assert.equal(host.selectedCharacter, before);
    assert.deepEqual(before.equipment, {});
    assert.deepEqual(host.toasts, ['Not saved. Sheet is locked']);
  });
});

describe('guardrail and hot-swap handlers never show success after an error', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('a refused guardrail save shows the error and keeps the old guardrails', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-1/guardrails': { body: { stance: 'cautious' } },
      'PUT /api/v1/characters/char-1/guardrails': { status: 503, body: { detail: 'Character service is unavailable.' } },
    });
    const host = makeHost();
    const before = host.selectedCharacter;

    await handleGuardrailsSaved(host, 'char-1', event({ riskThreshold: 'reckless' }));

    assert.equal(host.selectedCharacter, before);
    assert.equal(host.toasts.length, 1);
    assert.match(host.toasts[0], /^Not saved\. /);
  });

  it('a confirmed guardrail save shows success and puts new guardrails on the host', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-1/guardrails': { body: { stance: 'cautious', avoid_melee: false } },
      'PUT /api/v1/characters/char-1/guardrails': { body: {} },
    });
    const host = makeHost();
    const before = host.selectedCharacter;

    await handleGuardrailsSaved(host, 'char-1', event({ riskThreshold: 'reckless' }));

    assert.notEqual(host.selectedCharacter, before);
    assert.deepEqual(host.selectedCharacter.stand_in_guardrails, { stance: 'cautious', avoid_melee: false, riskThreshold: 'reckless' });
    assert.deepEqual(host.toasts, ['Tactical Guardrails Saved!']);
  });

  it('a guardrail save sends the full stored policy, keeps the stance, and omits the character id', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters/char-1/guardrails': { body: { stance: 'heroic' } },
      'PUT /api/v1/characters/char-1/guardrails': { body: {} },
    });
    const host = makeHost();

    await handleGuardrailsSaved(host, 'char-1', event({ characterId: 'char-1', avoid_melee: true }));

    assert.deepEqual(gateway.calls.map((c) => c.method), ['GET', 'PUT']);
    assert.deepEqual(gateway.calls[1].body, { stance: 'heroic', avoid_melee: true });
    assert.deepEqual(host.selectedCharacter.stand_in_guardrails, { stance: 'heroic', avoid_melee: true });
  });

  it('a refused hot-swap shows the error and no success text', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/sessions/session-1/hot-swap': { status: 403, body: { detail: 'Forbidden' } } });
    const host = makeHost();

    await handleHotSwapRequested(host, 'char-1', event({ characterId: 'char-1' }));

    assert.equal(host.toasts.length, 1);
    assert.match(host.toasts[0], /^Not saved\. /);
  });

  it('a confirmed hot-swap shows the transfer text', async () => {
    gateway = installFakeGateway({ 'POST /api/v1/sessions/session-1/hot-swap': { body: { status: 'control_transferred' } } });
    const host = makeHost();

    await handleHotSwapRequested(host, 'char-1', event({ characterId: 'char-1' }));

    assert.deepEqual(host.toasts, ['Hot-Swap Takeover Requested: Control transferred to player!']);
  });
});
