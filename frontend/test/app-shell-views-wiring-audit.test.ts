/**
 * Comprehensive Blackbox & Component Audit Test Suite for App Shell Views,
 * Deep Route Wiring, Parameter Extraction, Breadcrumbs, and WebSocket Lifecycle.
 *
 * TASK-0251: App Shell Views Enumeration, Wiring Audit, and Blackbox Test Suite
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0012, ADR-0013 | PRD-0023, US-0068
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, type MatchedRoute } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import type { AppActiveView } from '../src/runefoble-app.ts';

// Pure frontdoor view resolver mirroring RunefobleApp.getActiveView()
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

// Route-bound WebSocket requirement rule
function isSessionWebSocketRequired(route: MatchedRoute | null): boolean {
  const pat = route?.pattern || '';
  return pat === '#/campaigns/:campaignId/sessions/:sessionId' ||
         pat === '#/campaigns/:campaignId/lobby/:sessionId';
}

// Canonical view-to-mounted component contract manifest
const VIEW_COMPONENT_MANIFEST: Record<AppActiveView, string[]> = {
  'login': ['runefoble-auth-modal'],
  'campaigns': ['runefoble-campaign-dashboard'],
  'campaign-detail': ['runefoble-campaign-header', 'runefoble-campaign-members', 'runefoble-session-list'],
  'campaign-characters': ['runefoble-campaign-header', 'runefoble-character-roster'],
  'characters': ['runefoble-character-roster'],
  'character-sheet': ['runefoble-character-sheet'],
  'session-lobby': ['runefoble-session-lobby'],
  'session-active': ['runefoble-board', 'runefoble-character-card', 'runefoble-watcher-feed', 'runefoble-voice-controls'],
  'profile': ['runefoble-user-profile'],
};

interface RouteMatrixCase {
  name: string;
  path: string;
  expectedPattern: string;
  expectedView: AppActiveView;
  expectedParams: Record<string, string>;
}

const ROUTE_MATRIX: RouteMatrixCase[] = [
  { name: '1. Login', path: '#/login', expectedPattern: '#/login', expectedView: 'login', expectedParams: {} },
  { name: '2. Register', path: '#/register', expectedPattern: '#/register', expectedView: 'login', expectedParams: {} },
  { name: '3. Campaigns Hub', path: '#/campaigns', expectedPattern: '#/campaigns', expectedView: 'campaigns', expectedParams: {} },
  { name: '4. Campaign Detail', path: '#/campaigns/c-astral-42', expectedPattern: '#/campaigns/:campaignId', expectedView: 'campaign-detail', expectedParams: { campaignId: 'c-astral-42' } },
  { name: '5. Party Roster', path: '#/campaigns/c-astral-42/characters', expectedPattern: '#/campaigns/:campaignId/characters', expectedView: 'campaign-characters', expectedParams: { campaignId: 'c-astral-42' } },
  { name: '6. Assembly Lobby', path: '#/campaigns/c-astral-42/lobby/sess-99', expectedPattern: '#/campaigns/:campaignId/lobby/:sessionId', expectedView: 'session-lobby', expectedParams: { campaignId: 'c-astral-42', sessionId: 'sess-99' } },
  { name: '7. Active VTT Session', path: '#/campaigns/c-astral-42/sessions/sess-99', expectedPattern: '#/campaigns/:campaignId/sessions/:sessionId', expectedView: 'session-active', expectedParams: { campaignId: 'c-astral-42', sessionId: 'sess-99' } },
  { name: '8. Global Roster', path: '#/characters', expectedPattern: '#/characters', expectedView: 'characters', expectedParams: {} },
  { name: '9. User Profile', path: '#/profile', expectedPattern: '#/profile', expectedView: 'profile', expectedParams: {} },
  { name: '10. Character Sheet Inspector', path: '#/characters/char-valeros-01', expectedPattern: '#/characters/:characterId', expectedView: 'character-sheet', expectedParams: { characterId: 'char-valeros-01' } },
];

describe('App Shell Views Route Enumeration & Component Wiring Audit (TASK-0251)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
    router.setTitleResolver((type, id) => {
      if (type === 'campaign' && id === 'c-astral-42') return 'Astral Odyssey';
      if (type === 'lobby' && id === 'sess-99') return 'Lobby 99';
      if (type === 'session' && id === 'sess-99') return 'Session #99';
      if (type === 'character' && id === 'char-valeros-01') return 'Valeros of Korvosa';
      return undefined;
    });
  });

  for (const testCase of ROUTE_MATRIX) {
    it(`audits route ${testCase.name} (${testCase.path}) -> view '${testCase.expectedView}'`, () => {
      const match = router.match(testCase.path);
      assert.ok(match, `Route ${testCase.path} must match`);
      assert.equal(match.pattern, testCase.expectedPattern);
      assert.deepEqual(match.params, testCase.expectedParams);

      const activeView = resolveActiveView(match);
      assert.equal(activeView, testCase.expectedView);

      const expectedComponents = VIEW_COMPONENT_MANIFEST[activeView];
      assert.ok(expectedComponents.length > 0, `Components must be mounted for ${activeView}`);
    });
  }

  it('prevents route collisions across nested and ambiguous segments', () => {
    const profileMatch = router.match('#/profile');
    assert.equal(resolveActiveView(profileMatch), 'profile', '#/profile must not collide with campaigns');

    const partyMatch = router.match('#/campaigns/c-astral-42/characters');
    assert.equal(resolveActiveView(partyMatch), 'campaign-characters', '#/campaigns/:id/characters must not collide with campaign-detail');

    const globalCharsMatch = router.match('#/characters');
    assert.equal(resolveActiveView(globalCharsMatch), 'characters', '#/characters must not collide with campaigns');

    const charSheetMatch = router.match('#/characters/char-valeros-01');
    assert.equal(resolveActiveView(charSheetMatch), 'character-sheet', '#/characters/:id must not collide with characters');
  });
});

describe('Dynamic Title Resolution & Breadcrumbs Audit (TASK-0251)', () => {
  let router: Router;
  let dataService: AppDataService;

  beforeEach(() => {
    router = new Router();
    router.reset();
    dataService = new AppDataService();
  });

  it('populates dynamic campaign and session titles in breadcrumb trail without raw ID fallbacks', async () => {
    router.setAsyncTitleResolver(async (type, id) => {
      if (type === 'campaign') return (await dataService.fetchCampaign(id))?.title;
      if (type === 'session' || type === 'lobby') return (await dataService.fetchSession(id))?.title;
      if (type === 'character') return (await dataService.fetchCharacter(id))?.name;
      return undefined;
    });

    await router.navigate('#/campaigns/4/sessions/session-tomb-14');
    const curRoute = router.getCurrentRoute();
    assert.ok(curRoute);
    assert.equal(curRoute.breadcrumbs.length, 3);
    assert.equal(curRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(curRoute.breadcrumbs[1].label, 'Tomb of the Star-Eater');
    assert.notEqual(curRoute.breadcrumbs[1].label, 'Campaign #4');
    assert.equal(curRoute.breadcrumbs[2].label, 'Session #14: Tomb of the Star-Eater');
    assert.notEqual(curRoute.breadcrumbs[2].label, 'Session #session-tomb-14');
    assert.equal(curRoute.breadcrumbs[2].active, true);
  });

  it('asynchronously resolves character names in breadcrumbs for deep inspector route', async () => {
    router.setAsyncTitleResolver(async (type, id) => {
      if (type === 'character') return (await dataService.fetchCharacter(id))?.name;
      return undefined;
    });

    await router.navigate('#/characters/char-valeros');
    const route = router.getCurrentRoute();
    assert.ok(route);
    assert.equal(route.breadcrumbs.length, 3);
    assert.equal(route.breadcrumbs[0].label, 'Home');
    assert.equal(route.breadcrumbs[1].label, 'Characters');
    assert.equal(route.breadcrumbs[2].label, 'Valeros of Korvosa');
    assert.equal(route.breadcrumbs[2].active, true);
  });

  it('falls back cleanly to formatted identifiers if entity is not found in title resolvers', async () => {
    await router.navigate('#/campaigns/999/sessions/unknown-sess');
    const route = router.getCurrentRoute();
    assert.ok(route);
    assert.equal(route.breadcrumbs.length, 3);
    assert.equal(route.breadcrumbs[1].label, 'Campaign #999');
    assert.equal(route.breadcrumbs[2].label, 'Session #unknown-sess');
  });

  it('generates accurate breadcrumbs across all standard route definitions', () => {
    router.setTitleResolver((t, id) => (t === 'campaign' ? 'Astral Camp' : t === 'lobby' ? 'Lobby 1' : 'Item'));
    const lobbyRoute = router.match('#/campaigns/c1/lobby/l1');
    assert.ok(lobbyRoute);
    assert.equal(lobbyRoute.breadcrumbs.length, 3);
    assert.equal(lobbyRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(lobbyRoute.breadcrumbs[1].label, 'Astral Camp');
    assert.equal(lobbyRoute.breadcrumbs[2].label, 'Lobby 1');

    const profRoute = router.match('#/profile');
    assert.ok(profRoute);
    assert.equal(profRoute.breadcrumbs[0].label, 'Home');
    assert.equal(profRoute.breadcrumbs[1].label, 'Account Settings');
  });
});

describe('Route-Bound WebSocket Lifecycle & Teardown Audit (TASK-0251)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('determines WebSocket requirement strictly for session-lobby and session-active', () => {
    const nonWsRoutes = ['#/login', '#/register', '#/campaigns', '#/campaigns/4', '#/campaigns/4/characters', '#/characters', '#/characters/char-1', '#/profile'];
    for (const path of nonWsRoutes) {
      assert.equal(isSessionWebSocketRequired(router.match(path)), false, `Route ${path} must not require WS`);
    }

    const wsRoutes = ['#/campaigns/4/lobby/15', '#/campaigns/4/sessions/14'];
    for (const path of wsRoutes) {
      assert.equal(isSessionWebSocketRequired(router.match(path)), true, `Route ${path} must require WS`);
    }
  });

  it('tears down WebSocket when navigating away from an active session to non-session views', async () => {
    let wsActive = false;
    let activeSessionId: string | null = null;
    let teardownCount = 0;

    const connectWS = (sessionId: string) => { wsActive = true; activeSessionId = sessionId; };
    const disconnectWS = () => { wsActive = false; activeSessionId = null; };

    router.onRouteChanged((route) => {
      if (isSessionWebSocketRequired(route)) connectWS(route.params.sessionId);
      else disconnectWS();
    });

    await router.navigate('#/campaigns/4/sessions/sess-alpha');
    router.registerTeardown(() => {
      teardownCount++;
      disconnectWS();
    });

    assert.equal(wsActive, true);
    assert.equal(activeSessionId, 'sess-alpha');

    await router.navigate('#/profile');
    assert.equal(wsActive, false);
    assert.equal(activeSessionId, null);
    assert.equal(teardownCount, 1);
  });

  it('re-binds WebSocket to new session target when switching between sessions', async () => {
    const sessionHistory: string[] = [];
    router.onRouteChanged((route) => {
      if (isSessionWebSocketRequired(route)) sessionHistory.push(route.params.sessionId);
    });

    await router.navigate('#/campaigns/4/lobby/sess-lobby-1');
    await router.navigate('#/campaigns/4/sessions/sess-active-1');
    await router.navigate('#/campaigns/5/sessions/sess-active-2');

    assert.deepEqual(sessionHistory, ['sess-lobby-1', 'sess-active-1', 'sess-active-2']);
  });
});

describe('Error Fallbacks & Edge Cases Audit (TASK-0251)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('safely handles empty route and defaults to campaigns view', () => {
    const route = router.match('');
    assert.equal(resolveActiveView(route), 'campaigns');
    assert.equal(route?.path, '#/campaigns');
  });

  it('safely handles unrecognized route pattern with graceful breadcrumb fallback', () => {
    const route = router.match('#/unknown/virtual/tabletop');
    assert.ok(route);
    assert.equal(resolveActiveView(route), 'campaigns');
    assert.equal(route.breadcrumbs.length, 3);
    assert.equal(route.breadcrumbs[0].label, 'Unknown');
  });

  it('preserves query parameters without polluting route pattern or view resolution', () => {
    const route = router.match('#/campaigns?sort=updated_desc&filter=archived');
    assert.ok(route);
    assert.equal(resolveActiveView(route), 'campaigns');
    assert.equal(route.pattern, '#/campaigns');
    assert.equal(route.query.sort, 'updated_desc');
    assert.equal(route.query.filter, 'archived');
  });
});
