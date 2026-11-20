/**
 * The session binds the caller's own character, never another player's (TASK-0972).
 *
 * The roster holds every character the caller may view. The binding takes only the caller's
 * own character in the campaign, and prefers the caller's seat. With none, the result is null.
 * The gateway is faked at the fetch boundary. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { pickActiveCharacter } from '../../src/app/active-character.ts';
import { selectCharacterFromEvent, switchDmCharacter } from '../../src/app/character-actions.ts';
import { AppDataService } from '../../src/services/app-data-service.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';

const ALICE = 'user-alice';
const BOB = 'user-bob';

const valeros = { id: 'char-valeros', name: 'Valeros of Korvosa', campaignId: '4', ownerId: ALICE };
const kyra = { id: 'char-kyra', name: 'Kyra the Sun Maiden', campaignId: '4', ownerId: BOB };
const ezren = { id: 'char-ezren', name: 'Ezren the Gray', campaignId: '4', ownerId: ALICE };
const roster = [kyra, valeros];

describe('the active character is the caller own character', () => {
  it('binds Valeros to Alice and Kyra to Bob from the same roster', () => {
    assert.equal(pickActiveCharacter(roster, '4', ALICE, null)?.id, 'char-valeros');
    assert.equal(pickActiveCharacter(roster, '4', BOB, null)?.id, 'char-kyra');
  });

  it('binds null when the caller owns no character in the campaign', () => {
    assert.equal(pickActiveCharacter(roster, '4', 'user-carol', null), null);
  });

  it('never falls back to another player character when the caller has none in the campaign', () => {
    assert.equal(pickActiveCharacter([kyra], '4', ALICE, null), null);
  });

  it('ignores the caller characters in another campaign', () => {
    assert.equal(pickActiveCharacter([valeros], '9', ALICE, null), null);
  });

  it('binds null for an empty roster', () => {
    assert.equal(pickActiveCharacter([], '4', ALICE, null), null);
  });

  it('prefers the caller seat when the caller owns several characters in the campaign', () => {
    assert.equal(pickActiveCharacter([valeros, ezren], '4', ALICE, 'char-ezren')?.id, 'char-ezren');
  });

  it('ignores a seat that another player holds', () => {
    assert.equal(pickActiveCharacter([valeros, kyra], '4', ALICE, 'char-kyra')?.id, 'char-valeros');
  });

  it('binds null for an unowned character (empty owner) even when it is the only one', () => {
    const unowned = { ...valeros, ownerId: '' };
    assert.equal(pickActiveCharacter([unowned], '4', '', null), null);
  });
});

describe('the character read maps the owner of each character', () => {
  let gateway: FakeGateway | undefined;
  afterEach(() => { gateway?.restore(); gateway = undefined; });

  it('maps owner_id from the owner wire to ownerId', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters': { body: [{ id: 'char-valeros', name: 'Valeros', campaign_id: '4', owner_id: ALICE }] },
    });
    const res = await new AppDataService().fetchCharacters();
    assert.ok(res.ok);
    assert.equal(res.data[0].ownerId, ALICE);
  });

  it('fails the read when a character carries no owner', async () => {
    gateway = installFakeGateway({
      'GET /api/v1/characters': { body: [{ id: 'char-valeros', name: 'Valeros', campaign_id: '4' }] },
    });
    const res = await new AppDataService().fetchCharacters();
    assert.equal(res.ok, false);
  });
});

function host(overrides: Record<string, unknown> = {}) {
  return {
    currentUserId: ALICE,
    characters: [kyra, valeros],
    activeCharacter: null as any,
    lobbyParticipants: [] as any[],
    campaignCapabilities: { run_session: false, play: true },
    toasts: [] as string[],
    showToast(m: string) { this.toasts.push(m); },
    ...overrides,
  };
}

describe('the lobby and the DM inspector never bind another player character', () => {
  it('does not bind a character that another player owns when the caller picks it', async () => {
    const h = host();
    await selectCharacterFromEvent(h as any, new CustomEvent('select-character', { detail: { characterId: 'char-kyra' } }));
    assert.equal(h.activeCharacter, null);
  });

  it('binds the caller own character when the caller picks it', async () => {
    const h = host();
    await selectCharacterFromEvent(h as any, new CustomEvent('select-character', { detail: { characterId: 'char-valeros' } }));
    assert.equal(h.activeCharacter?.id, 'char-valeros');
  });

  it('lets a DM with the run-session capability inspect another character', () => {
    const h = host({ campaignCapabilities: { run_session: true, play: false } });
    switchDmCharacter(h as any, 'char-kyra');
    assert.equal(h.activeCharacter?.id, 'char-kyra');
  });

  it('refuses the DM inspector switch without the run-session capability', () => {
    const h = host();
    switchDmCharacter(h as any, 'char-kyra');
    assert.equal(h.activeCharacter, null);
  });
});
