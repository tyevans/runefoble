/**
 * View resolver and route state tests (TASK-0643).
 * Every route in the matrix resolves to exactly one view. The route state follows the route.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router } from '../src/router/router.ts';
import { resolveActiveView } from '../src/router/view-resolver.ts';
import { applyRouteState } from '../src/app/route-state.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

const MATRIX: Array<[string, string]> = [
  ['#/login', 'login'],
  ['#/register', 'login'],
  ['#/campaigns', 'campaigns'],
  ['#/campaigns/c1', 'campaign-detail'],
  ['#/campaigns/c1/characters', 'campaign-characters'],
  ['#/campaigns/c1/codex', 'campaign-codex'],
  ['#/campaigns/c1/analytics', 'campaign-analytics'],
  ['#/campaigns/c1/forge', 'campaign-forge'],
  ['#/campaigns/c1/lobby/s1', 'session-lobby'],
  ['#/campaigns/c1/sessions/s1', 'session-active'],
  ['#/characters', 'characters'],
  ['#/characters/ch1', 'character-sheet'],
  ['#/profile', 'profile'],
  ['#/caravans/frontier-1', 'caravan-board'],
];

describe('resolveActiveView', () => {
  for (const [path, view] of MATRIX) {
    it(`resolves ${path} to ${view}`, () => {
      assert.equal(resolveActiveView(new Router().match(path)), view);
    });
  }

  it('resolves a missing route to the campaign hub', () => {
    assert.equal(resolveActiveView(null), 'campaigns');
  });
});

describe('applyRouteState', () => {
  it('copies route identifiers into the host and opens the auth modal on login', () => {
    const host: any = { selectedCharacterId: '', isAuthModalOpen: false };
    applyRouteState(host, new Router().match('#/campaigns/c1/sessions/s1')!);
    assert.equal(host.campaignId, 'c1');
    assert.equal(host.sessionId, 's1');
    assert.equal(host.isAuthModalOpen, false);
    applyRouteState(host, new Router().match('#/login')!);
    assert.equal(host.isAuthModalOpen, true);
    assert.equal(host.campaignId, '');
  });
});

describe('fetchSession without a title', () => {
  let gateway: FakeGateway;
  afterEach(() => gateway.restore());

  it('returns an empty title and never invents one', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/sessions/s9': { body: { id: 's9', campaign_id: 'c1' } } });
    const result = await new AppDataService().fetchSession('s9');
    assert.ok(result.ok);
    assert.equal(result.data.title, '');
  });
});
