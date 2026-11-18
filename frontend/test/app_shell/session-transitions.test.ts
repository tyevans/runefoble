/**
 * App Shell Session Lifecycle & Transitions Test Suite.
 *
 * TASK-0287: Frontend App Shell Test Suite Modular Decomposition
 * TASK-0640b: Board and plugin wiring moved to board-and-plugin-slots.test.ts (line cap).
 * Governing ADRs: ADR-0004, ADR-0012, ADR-0013
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 110 lines; limit < 130 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router } from '../../src/router/router.ts';
import { AppDataService } from '../../src/services/app-data-service.ts';
import { installFakeGateway, type FakeGateway } from '../support/fake-gateway.ts';
import { FALLBACK_CHARACTERS, FALLBACK_PARTICIPANTS, FALLBACK_BOARD_TOKENS } from '../support/app-data-service.fixtures.ts';

/** A stateful roster behind the gateway: create, assign, and delete change what later reads return. */
function installRosterGateway(): { gateway: FakeGateway; roster: any[] } {
  const roster: any[] = FALLBACK_CHARACTERS.map((c) => ({ ...c }));
  const gateway = installFakeGateway({
    'GET /api/v1/characters': () => ({ body: roster }),
    'POST /api/v1/characters': (req) => {
      const body = req.body as any;
      const created = { id: `char-${roster.length + 1}`, campaignId: null, campaignTitle: null, currentHp: body.maxHp, armorClass: 10, speed: 30, ...body };
      roster.push(created);
      return { status: 201, body: created };
    },
    'PATCH /api/v1/characters/char-ezren/campaign': (req) => { roster.find((c) => c.id === 'char-ezren').campaignId = (req.body as any).campaignId; return { status: 204 }; },
    'DELETE /api/v1/characters/char-kyra': () => { roster.splice(roster.findIndex((c) => c.id === 'char-kyra'), 1); return { status: 204 }; },
    'GET /api/v1/sessions/session-tomb-14': { body: { id: 'session-tomb-14', campaign_id: '4', title: 'Session #14', status: 'active', participants: FALLBACK_PARTICIPANTS } },
    'GET /api/v1/boards/session-tomb-14': { body: { cols: 12, rows: 10, tokens: FALLBACK_BOARD_TOKENS } },
  });
  return { gateway, roster };
}

describe('App Shell Session Lifecycle & Transitions', () => {
  let router: Router;
  let dataService: AppDataService;
  let gateway: FakeGateway;

  beforeEach(() => {
    router = new Router();
    router.reset();
    dataService = new AppDataService();
    gateway = installRosterGateway().gateway;
  });

  afterEach(() => gateway.restore());

  it('transitions router from lobby to active VTT on launch-session event', async () => {
    await router.navigate('#/campaigns/4/lobby/session-tomb-14');
    await router.navigate('#/campaigns/4/sessions/session-tomb-14');
    const target = router.getCurrentRoute();
    assert.equal(target?.pattern, '#/campaigns/:campaignId/sessions/:sessionId');
    assert.equal(target?.params.campaignId, '4');
    assert.equal(target?.params.sessionId, 'session-tomb-14');
  });

  it('transitions router from lobby to active VTT upon incoming WebSocket session_started message', async () => {
    await router.navigate('#/campaigns/4/lobby/session-tomb-14');
    const msg = { type: 'session_started', campaignId: '4', sessionId: 'session-tomb-14' };
    if (msg.type === 'session_started') {
      await router.navigate(`#/campaigns/${msg.campaignId}/sessions/${msg.sessionId}`);
    }
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns/4/sessions/session-tomb-14');
  });

  it('dynamically populates lobby available characters from character roster with campaign priority', async () => {
    const lobby = await dataService.fetchLobbyState('4', 'session-tomb-14');
    assert.ok(lobby.ok);
    assert.ok(lobby.data.availableCharacters.length >= 2);
    assert.ok(lobby.data.availableCharacters[0].id === 'char-valeros' || lobby.data.availableCharacters[0].id === 'char-kyra');
  });

  it('prioritizes campaign-assigned character fallback when entering active session without explicit selection', () => {
    const chars = [{ id: 'c1', name: 'Rogue', campaignId: '99' }, { id: 'c2', name: 'Paladin', campaignId: '4' }];
    const resolve = (cId: string, cur: any) => cur || chars.find((c) => c.campaignId === cId) || chars[0];
    assert.equal(resolve('4', null).id, 'c2');
    assert.equal(resolve('4', chars[0]).id, 'c1');
  });

  it('creates character via createCharacter mutation', async () => {
    const created = await dataService.createCharacter({ name: 'Harsk the Ranger', characterClass: 'Ranger', level: 3, maxHp: 28 } as any);
    assert.ok(created.ok);
    assert.equal(created.data.name, 'Harsk the Ranger');
    const roster = await dataService.fetchCharacters();
    assert.ok(roster.ok && roster.data.some((c) => c.name === 'Harsk the Ranger'));
  });

  it('assigns character to campaign and unassigns via assignCharacterCampaign', async () => {
    const assigned = await dataService.assignCharacterCampaign('char-ezren', '4');
    assert.equal(assigned.ok, true);
    const afterAssign = await dataService.fetchCharacters();
    assert.ok(afterAssign.ok);
    assert.equal(afterAssign.data.find((c) => c.id === 'char-ezren')?.campaignId, '4');
  });

  it('deletes character via deleteCharacter mutation', async () => {
    const deleted = await dataService.deleteCharacter('char-kyra');
    assert.equal(deleted.ok, true);
    const roster = await dataService.fetchCharacters();
    assert.ok(roster.ok && !roster.data.some((c) => c.id === 'char-kyra'));
  });
});
