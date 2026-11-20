/**
 * Character Creation, Campaign Filtering & State Mutations Test Suite.
 *
 * TASK-0288: Frontend Character Management Test Suite Modular Decomposition
 * TASK-0640: Creation and failure results are checked at the fetch boundary.
 * Sub-resource mutations live in mutations.test.ts.
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0012, ADR-0013, ADR-0014
 * Hard Invariants: Hard Invariant 6 (< 130 lines), Hard Invariant 7 (Blackbox TDD)
 */

import { PORTRAIT_PLACEHOLDERS } from '@runefoble/ui-core';
import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { AppDataService } from '../../src/services/app-data-service.ts';
import type { CharacterItem, CreateCharacterPayload } from '../../../services/character_sheet/ui/src/roster/types.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';

describe('Character Creation & Data Mutations (TASK-0288, PRD-0006)', () => {
  let gateway: FakeGateway | undefined;

  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('test_character_creation_and_unassigned_roster: persists new character in unassigned state', async () => {
    const roster: CharacterItem[] = [];
    gateway = installFakeGateway({
      'POST /api/v1/characters': (req) => {
        const body = req.body as any;
        const created = { id: 'char-seoni', name: body.name, characterClass: body.characterClass, level: body.level, currentHp: body.maxHp, maxHp: body.maxHp, armorClass: body.armorClass, campaignId: null, owner_id: 'user-signed-in' };
        roster.push(created as CharacterItem);
        return { status: 201, body: created };
      },
      'GET /api/v1/characters': () => ({ body: roster }),
    });
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
      portraitUrl: PORTRAIT_PLACEHOLDERS.wizard,
    };
    const created = await dataService.createCharacter(payload);
    assert.ok(created.ok);
    assert.ok(created.data.id, 'Created character must have an ID');
    assert.equal(created.data.name, 'Seoni of Varisia');
    assert.equal(created.data.currentHp, 22);

    const all = await dataService.fetchCharacters();
    assert.ok(all.ok);
    const found = all.data.find((c) => c.name === 'Seoni of Varisia');
    assert.ok(found, 'New character must appear in roster');
    assert.ok(found?.campaignId == null, 'New character should start unassigned');
  });

  it('test_create_character_failure_adds_nothing_locally: a rejected create returns a typed error', async () => {
    gateway = installFakeGateway({
      'POST /api/v1/characters': { status: 422, body: { detail: 'name must not be empty' } },
    });
    const result = await new AppDataService().createCharacter({ name: '' } as CreateCharacterPayload);
    assert.equal(result.ok, false);
    assert.equal(result.ok === false && result.status, 422);
    assert.equal(result.ok === false && result.message, 'name must not be empty');
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

  it('test_restore_spell_slot_reports_missing_route: no local slot is restored without a server route', async () => {
    gateway = installFakeGateway({});
    const result = await AppDataService.getInstance().restoreCharacterSpellSlot('char-valeros', 1);
    assert.equal(result.ok, false);
    assert.equal(result.ok === false && result.status, 501);
    assert.equal(gateway.calls.length, 0);
  });
});
