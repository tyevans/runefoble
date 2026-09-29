/**
 * App Shell State & Breadcrumbs Orchestration Test Suite.
 *
 * TASK-0287: Frontend App Shell Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0012, ADR-0013
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 100 lines; limit < 130 lines)
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

describe('App Shell State & Breadcrumbs Orchestration', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('orchestrates active view state transitions across app sections', async () => {
    const viewHistory: AppActiveView[] = [];
    router.onRouteChanged((route) => {
      viewHistory.push(resolveActiveView(route));
    });

    await router.navigate('#/campaigns');
    await router.navigate('#/campaigns/4');
    await router.navigate('#/campaigns/4/characters');
    await router.navigate('#/characters');
    await router.navigate('#/profile');

    assert.deepEqual(viewHistory, ['campaigns', 'campaign-detail', 'campaign-characters', 'characters', 'profile']);
  });

  it('updates breadcrumb trail dynamically on hierarchical navigation', async () => {
    router.setTitleResolver((type, id) => {
      if (type === 'campaign' && id === '4') return 'Tomb of the Star-Eater';
      if (type === 'session' && id === '14') return 'Session #14';
      return undefined;
    });

    await router.navigate('#/campaigns/4/sessions/14');
    const crumbs = router.getCurrentRoute()?.breadcrumbs || [];

    assert.equal(crumbs.length, 3);
    assert.equal(crumbs[0].label, 'Campaigns'); assert.equal(crumbs[0].path, '#/campaigns');
    assert.equal(crumbs[1].label, 'Tomb of the Star-Eater'); assert.equal(crumbs[1].path, '#/campaigns/4');
    assert.equal(crumbs[2].label, 'Session #14'); assert.equal(crumbs[2].path, '#/campaigns/4/sessions/14');
    assert.equal(crumbs[2].active, true);
  });

  it('resolves dynamic entity titles asynchronously with caching', async () => {
    let fetchCount = 0;
    router.setAsyncTitleResolver(async (type, id) => {
      fetchCount++;
      return type === 'character' && id === 'char-valeros' ? 'Valeros of Korvosa' : undefined;
    });

    await router.navigate('#/characters/char-valeros');
    let crumbs = router.getCurrentRoute()?.breadcrumbs || [];
    assert.equal(crumbs[crumbs.length - 1].label, 'Valeros of Korvosa');
    assert.equal(fetchCount, 1);

    await router.navigate('#/characters/char-valeros');
    crumbs = router.getCurrentRoute()?.breadcrumbs || [];
    assert.equal(crumbs[crumbs.length - 1].label, 'Valeros of Korvosa');
    assert.equal(fetchCount, 1);
  });

  it('verifies browser history and route state tracking on navigation', async () => {
    await router.navigate('#/campaigns');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');

    await router.navigate('#/characters');
    assert.equal(router.getCurrentRoute()?.path, '#/characters');

    await router.navigate('#/campaigns/4/lobby/15');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns/4/lobby/15');
    assert.equal(router.getCurrentRoute()?.params.campaignId, '4');
    assert.equal(router.getCurrentRoute()?.params.sessionId, '15');
  });
});
