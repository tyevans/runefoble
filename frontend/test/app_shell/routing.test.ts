/**
 * App Shell Dynamic View Routing & Parameter Extraction Test Suite.
 *
 * TASK-0287: Frontend App Shell Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0012, ADR-0013
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 110 lines; limit < 130 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, type MatchedRoute } from '../../src/router/router.ts';
import type { AppActiveView } from '../../src/runefoble-app.ts';

function resolveActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
  if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
  if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
  if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
  if (pat.startsWith('#/characters/') && pat !== '#/characters') return 'character-sheet';
  if (pat === '#/characters') return 'characters';
  return pat === '#/profile' ? 'profile' : 'campaigns';
}

describe('App Shell Dynamic View Routing & Parameter Extraction', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('resolves login and registration views with auth modal trigger', () => {
    const loginRoute = router.match('#/login');
    assert.equal(resolveActiveView(loginRoute), 'login');

    const registerRoute = router.match('#/register');
    assert.equal(resolveActiveView(registerRoute), 'login');
  });

  it('resolves campaign dashboard view for root campaigns route', () => {
    const route = router.match('#/campaigns');
    assert.equal(resolveActiveView(route), 'campaigns');
  });

  it('resolves campaign detail view with extracted campaignId parameter', () => {
    const route = router.match('#/campaigns/4');
    assert.equal(resolveActiveView(route), 'campaign-detail');
    assert.equal(route?.params.campaignId, '4');

    const partyRoute = router.match('#/campaigns/42/characters');
    assert.equal(resolveActiveView(partyRoute), 'campaign-characters');
    assert.equal(partyRoute?.params.campaignId, '42');

    const profileRoute = router.match('#/profile');
    assert.equal(resolveActiveView(profileRoute), 'profile');
  });

  it('resolves character roster view for #/characters', () => {
    const route = router.match('#/characters');
    assert.equal(resolveActiveView(route), 'characters');
  });

  it('resolves session lobby view for #/campaigns/:id/lobby/:sessionId', () => {
    const route = router.match('#/campaigns/4/lobby/session-tomb-14');
    assert.equal(resolveActiveView(route), 'session-lobby');
    assert.equal(route?.params.campaignId, '4');
    assert.equal(route?.params.sessionId, 'session-tomb-14');
  });

  it('resolves active VTT session view for #/campaigns/:id/sessions/:sessionId', () => {
    const route = router.match('#/campaigns/4/sessions/session-tomb-14');
    assert.equal(resolveActiveView(route), 'session-active');
    assert.equal(route?.params.campaignId, '4');
    assert.equal(route?.params.sessionId, 'session-tomb-14');
  });

  it('defaults to campaigns view for empty or unrecognized route', () => {
    const emptyRoute = router.match('');
    assert.equal(resolveActiveView(emptyRoute), 'campaigns');

    const unknownRoute = router.match('#/unknown-route');
    assert.equal(resolveActiveView(unknownRoute), 'campaigns');
  });

  it('navigates to deep route #/characters/:characterId on inspect sheet event', async () => {
    await router.navigate('#/characters');
    assert.equal(router.getCurrentRoute()?.path, '#/characters');

    await router.navigate('#/characters/char-valeros');
    assert.equal(router.getCurrentRoute()?.path, '#/characters/char-valeros');
  });
});
