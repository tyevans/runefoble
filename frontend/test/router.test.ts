/**
 * Unit tests for Runefoble SPA Router
 * TASK-0206: Frontend SPA Client Router and Navigation Chrome
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Router, STANDARD_ROUTES } from '../src/router/router.ts';

describe('Router Pattern Matcher & Parameter Extraction', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.setTitleResolver((type, id) => {
      if (type === 'campaign' && id === '4') return 'Tomb of the Star-Eater';
      if (type === 'lobby' && id === '15') return 'Lobby 15';
      if (type === 'session' && id === '14') return 'Session #14';
      if (type === 'character' && id === 'char-valeros') return 'Valeros of Korvosa';
      return undefined;
    });
  });

  it('declares all required standard routes', () => {
    const required = [
      '#/login',
      '#/register',
      '#/campaigns',
      '#/campaigns/:campaignId',
      '#/campaigns/:campaignId/characters',
      '#/campaigns/:campaignId/lobby/:sessionId',
      '#/campaigns/:campaignId/sessions/:sessionId',
      '#/characters',
      '#/characters/:characterId',
      '#/profile',
    ];
    for (const r of required) {
      assert.ok(
        (STANDARD_ROUTES as readonly string[]).includes(r),
        `Route ${r} must be in STANDARD_ROUTES`
      );
    }
  });

  it('matches static routes correctly', () => {
    const mLogin = router.match('#/login');
    assert.ok(mLogin);
    assert.equal(mLogin.pattern, '#/login');
    assert.deepEqual(mLogin.params, {});

    const mCamp = router.match('#/campaigns');
    assert.ok(mCamp);
    assert.equal(mCamp.pattern, '#/campaigns');

    const mChars = router.match('#/characters');
    assert.ok(mChars);
    assert.equal(mChars.pattern, '#/characters');

    const mProf = router.match('#/profile');
    assert.ok(mProf);
    assert.equal(mProf.pattern, '#/profile');
  });

  it('extracts parameters for campaign details, lobby, and sessions', () => {
    const mDetails = router.match('#/campaigns/42');
    assert.ok(mDetails);
    assert.equal(mDetails.pattern, '#/campaigns/:campaignId');
    assert.equal(mDetails.params.campaignId, '42');

    const mParty = router.match('#/campaigns/42/characters');
    assert.ok(mParty);
    assert.equal(mParty.pattern, '#/campaigns/:campaignId/characters');
    assert.equal(mParty.params.campaignId, '42');

    const mLobby = router.match('#/campaigns/42/lobby/sess-99');
    assert.ok(mLobby);
    assert.equal(mLobby.pattern, '#/campaigns/:campaignId/lobby/:sessionId');
    assert.equal(mLobby.params.campaignId, '42');
    assert.equal(mLobby.params.sessionId, 'sess-99');

    const mSession = router.match('#/campaigns/4/sessions/14');
    assert.ok(mSession);
    assert.equal(mSession.pattern, '#/campaigns/:campaignId/sessions/:sessionId');
    assert.equal(mSession.params.campaignId, '4');
    assert.equal(mSession.params.sessionId, '14');

    const mChar = router.match('#/characters/char-valeros');
    assert.ok(mChar);
    assert.equal(mChar.pattern, '#/characters/:characterId');
    assert.equal(mChar.params.characterId, 'char-valeros');
    assert.equal(mChar.breadcrumbs.length, 3);
    assert.equal(mChar.breadcrumbs[0].label, 'Home');
    assert.equal(mChar.breadcrumbs[0].path, '#/campaigns');
    assert.equal(mChar.breadcrumbs[1].label, 'Characters');
    assert.equal(mChar.breadcrumbs[1].path, '#/characters');
    assert.equal(mChar.breadcrumbs[2].label, 'Valeros of Korvosa');
    assert.equal(mChar.breadcrumbs[2].path, '#/characters/char-valeros');
    assert.equal(mChar.breadcrumbs[2].active, true);
  });

  it('parses URL query parameters correctly', () => {
    const matched = router.match('#/campaigns?mode=active&page=2');
    assert.ok(matched);
    assert.equal(matched.query.mode, 'active');
    assert.equal(matched.query.page, '2');
  });

  it('generates hierarchical breadcrumbs with title resolution', () => {
    const matched = router.match('#/campaigns/4/sessions/14');
    assert.ok(matched);
    const crumbs = matched.breadcrumbs;
    assert.equal(crumbs.length, 3);
    assert.equal(crumbs[0].label, 'Campaigns');
    assert.equal(crumbs[0].path, '#/campaigns');
    assert.equal(crumbs[1].label, 'Tomb of the Star-Eater');
    assert.equal(crumbs[1].path, '#/campaigns/4');
    assert.equal(crumbs[2].label, 'Session #14');
    assert.equal(crumbs[2].active, true);
  });

  it('generates fallback breadcrumbs for unregistered paths', () => {
    const crumbs = router.match('#/unknown/subpath');
    assert.ok(crumbs);
    assert.equal(crumbs.breadcrumbs.length, 2);
    assert.equal(crumbs.breadcrumbs[0].label, 'Unknown');
    assert.equal(crumbs.breadcrumbs[1].label, 'Subpath');
  });
});

describe('Router Navigation, Guards & Teardown Lifecycle', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('notifies route listeners on navigation', async () => {
    let notifiedRoute: string | null = null;
    let prevRoute: string | null = null;

    router.onRouteChanged((curr, prev) => {
      notifiedRoute = curr.path;
      prevRoute = prev ? prev.path : null;
    });

    await router.navigate('#/campaigns');
    assert.equal(notifiedRoute, '#/campaigns');
    assert.equal(prevRoute, null);

    await router.navigate('#/characters');
    assert.equal(notifiedRoute, '#/characters');
    assert.equal(prevRoute, '#/campaigns');
  });

  it('enforces route guard aborting navigation when returning false', async () => {
    await router.navigate('#/campaigns');

    router.beforeEach((to) => {
      if (to.path === '#/profile') return false;
      return true;
    });

    const success = await router.navigate('#/profile');
    assert.equal(success, false);
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');
  });

  it('enforces route guard redirecting to login when unauthenticated', async () => {
    let isAuthenticated = false;

    router.beforeEach((to) => {
      if (!isAuthenticated && to.path !== '#/login') {
        return '#/login';
      }
      return true;
    });

    const success = await router.navigate('#/campaigns/4/sessions/14');
    assert.equal(success, true);
    assert.equal(router.getCurrentRoute()?.path, '#/login');

    isAuthenticated = true;
    await router.navigate('#/campaigns/4/sessions/14');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns/4/sessions/14');
  });

  it('executes teardown handlers when navigating away from a route', async () => {
    let socketClosed = false;
    let audioHalted = false;

    await router.navigate('#/campaigns/4/sessions/14');

    router.registerTeardown(() => {
      socketClosed = true;
    });
    router.registerTeardown(() => {
      audioHalted = true;
    });

    assert.equal(socketClosed, false);
    assert.equal(audioHalted, false);

    // Navigate to campaigns dashboard
    await router.navigate('#/campaigns');

    assert.equal(socketClosed, true);
    assert.equal(audioHalted, true);
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');
  });
});

describe('Vite Proxy Configuration (TASK-0247)', () => {
  it('configures reverse proxy for /api/v1 to gateway backend with changeOrigin', async () => {
    const viteConfig = (await import('../vite.config.ts')).default;
    const proxy = (viteConfig as any).server?.proxy;
    assert.ok(proxy, 'server.proxy must be configured');
    assert.ok(proxy['/api/v1'], 'proxy must contain /api/v1 mapping');
    assert.equal(proxy['/api/v1'].target, process.env.GATEWAY_API_URL || 'http://localhost:8000');
    assert.equal(proxy['/api/v1'].changeOrigin, true);
  });

  it('configures websocket proxy for /ws with ws protocol and flag', async () => {
    const viteConfig = (await import('../vite.config.ts')).default;
    const proxy = (viteConfig as any).server?.proxy;
    assert.ok(proxy, 'server.proxy must be configured');
    assert.ok(proxy['/ws'], 'proxy must contain /ws mapping');
    const expectedWs = process.env.GATEWAY_WS_URL || (process.env.GATEWAY_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
    assert.equal(proxy['/ws'].target, expectedWs);
    assert.equal(proxy['/ws'].ws, true);
  });
});

describe('Dynamic Route Title Resolution & Async Caching (TASK-0247)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('asynchronously resolves entity titles and updates breadcrumbs during navigation', async () => {
    let callCount = 0;
    router.setAsyncTitleResolver(async (type, id) => {
      callCount++;
      if (type === 'campaign' && id === 'camp-1790564858218') {
        return 'Curse of the Frost Giant';
      }
      if (type === 'session' && id === 'sess-deep-44') {
        return 'Session #44: The Frozen Gate';
      }
      return undefined;
    });

    await router.navigate('#/campaigns/camp-1790564858218');
    const current = router.getCurrentRoute();
    assert.ok(current);
    assert.equal(current.breadcrumbs.length, 2);
    assert.equal(current.breadcrumbs[0].label, 'Campaigns');
    assert.equal(current.breadcrumbs[1].label, 'Curse of the Frost Giant');
    assert.equal(current.breadcrumbs[1].active, true);

    // Navigate to session
    await router.navigate('#/campaigns/camp-1790564858218/sessions/sess-deep-44');
    const sessRoute = router.getCurrentRoute();
    assert.ok(sessRoute);
    assert.equal(sessRoute.breadcrumbs.length, 3);
    assert.equal(sessRoute.breadcrumbs[0].label, 'Campaigns');
    assert.equal(sessRoute.breadcrumbs[1].label, 'Curse of the Frost Giant');
    assert.equal(sessRoute.breadcrumbs[2].label, 'Session #44: The Frozen Gate');

    // Verify caching: calling resolveTitle synchronously returns cached title without re-fetching
    const cached = router.resolveTitle('campaign', 'camp-1790564858218');
    assert.equal(cached, 'Curse of the Frost Giant');
    const prevCalls = callCount;
    const asyncCached = await router.resolveTitleAsync('campaign', 'camp-1790564858218');
    assert.equal(asyncCached, 'Curse of the Frost Giant');
    assert.equal(callCount, prevCalls, 'Cached title must not invoke resolver again');
  });

  it('falls back to default identifier formatting if title resolution returns undefined', async () => {
    router.setAsyncTitleResolver(async () => undefined);

    await router.navigate('#/campaigns/camp-unknown-999');
    const current = router.getCurrentRoute();
    assert.ok(current);
    assert.equal(current.breadcrumbs[1].label, 'Campaign #camp-unknown-999');
  });

  it('asynchronously resolves character names and updates character sheet breadcrumbs', async () => {
    router.setAsyncTitleResolver(async (type, id) => {
      if (type === 'character' && id === 'char-shadow') {
        return 'Theron Shadowblade';
      }
      return undefined;
    });

    await router.navigate('#/characters/char-shadow');
    const current = router.getCurrentRoute();
    assert.ok(current);
    assert.equal(current.pattern, '#/characters/:characterId');
    assert.equal(current.params.characterId, 'char-shadow');
    assert.equal(current.breadcrumbs.length, 3);
    assert.equal(current.breadcrumbs[0].label, 'Home');
    assert.equal(current.breadcrumbs[0].path, '#/campaigns');
    assert.equal(current.breadcrumbs[1].label, 'Characters');
    assert.equal(current.breadcrumbs[1].path, '#/characters');
    assert.equal(current.breadcrumbs[2].label, 'Theron Shadowblade');
    assert.equal(current.breadcrumbs[2].active, true);
  });
});
