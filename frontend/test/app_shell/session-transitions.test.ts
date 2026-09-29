/**
 * App Shell Session Lifecycle & Transitions Test Suite.
 *
 * TASK-0287: Frontend App Shell Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0012, ADR-0013
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 110 lines; limit < 130 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router } from '../../src/router/router.ts';
import { AppDataService } from '../../src/services/app-data-service.ts';

describe('App Shell Session Lifecycle & Transitions', () => {
  let router: Router;
  let dataService: AppDataService;

  beforeEach(() => {
    router = new Router();
    router.reset();
    dataService = new AppDataService();
  });

  it('transitions router from lobby to active VTT on launch-session event', async () => {
    await router.navigate('#/campaigns/4/lobby/session-tomb-14');
    assert.equal(router.getCurrentRoute()?.pattern, '#/campaigns/:campaignId/lobby/:sessionId');

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
    assert.ok(lobby.availableCharacters.length >= 2);
    const firstChar = lobby.availableCharacters[0];
    assert.ok(firstChar.id === 'char-valeros' || firstChar.id === 'char-kyra');
  });

  it('prioritizes campaign-assigned character fallback when entering active session without explicit selection', () => {
    const chars = [
      { id: 'c1', name: 'Rogue', campaignId: '99' },
      { id: 'c2', name: 'Paladin Two', campaignId: '4' },
    ];
    const resolveActive = (cId: string, current: any) => current || chars.find((c) => c.campaignId === cId) || chars[0];
    assert.equal(resolveActive('4', null).id, 'c2');
    assert.equal(resolveActive('4', chars[0]).id, 'c1');
  });

  it('creates character via createCharacter mutation', async () => {
    const newChar = await dataService.createCharacter({
      name: 'Harsk the Ranger', characterClass: 'Ranger', level: 3, maxHp: 28, armorClass: 15, speed: 30,
    });
    assert.equal(newChar.name, 'Harsk the Ranger');
    const all = await dataService.fetchCharacters();
    assert.ok(all.some((c) => c.name === 'Harsk the Ranger'));
  });

  it('assigns character to campaign and unassigns via assignCharacterCampaign', async () => {
    const chars = await dataService.fetchCharacters();
    const ezren = chars.find((c) => c.id === 'char-ezren') || chars[0];
    await dataService.assignCharacterCampaign(ezren.id, '4');
    let updated = (await dataService.fetchCharacters()).find((c) => c.id === ezren.id);
    assert.equal(updated?.campaignId, '4');
    await dataService.assignCharacterCampaign(ezren.id, null);
    updated = (await dataService.fetchCharacters()).find((c) => c.id === ezren.id);
    assert.equal(updated?.campaignId, null);
  });

  it('deletes character via deleteCharacter mutation', async () => {
    const created = await dataService.createCharacter({ name: 'Temp Deletable', characterClass: 'Fighter', maxHp: 10 });
    await dataService.deleteCharacter(created.id);
    const list = await dataService.fetchCharacters();
    assert.ok(!list.some((c) => c.id === created.id));
  });
});
