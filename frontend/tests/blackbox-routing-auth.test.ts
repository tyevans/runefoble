/**
 * Blackbox Frontdoor Test Suite for Frontend SPA Routing & Zitadel Auth.
 * TASK-0214 / PRD-0023 / US-0062 / US-0066.
 * Governing ADRs: ADR-0004, ADR-0005, ADR-0013.
 * Hard Invariant 6 (<250 lines), Hard Invariant 7 (Blackbox Frontdoor TDD).
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

// Public Browser Environment Harness (DOM events, Hash, and LocalStorage)
class BrowserLocalStorage {
  private store = new Map<string, string>();
  getItem(k: string): string | null { return this.store.get(k) ?? null; }
  setItem(k: string, v: string): void { this.store.set(k, String(v)); }
  removeItem(k: string): void { this.store.delete(k); }
  clear(): void { this.store.clear(); }
}

const mockStorage = new BrowserLocalStorage();
const browserEvents = new EventTarget();

class BrowserHistoryHarness {
  public stack: string[] = [];
  public index = -1;

  navigate(hash: string) {
    if (this.index < this.stack.length - 1) this.stack = this.stack.slice(0, this.index + 1);
    this.stack.push(hash);
    this.index = this.stack.length - 1;
    this.dispatch(hash);
  }

  back() {
    if (this.index > 0) { this.index--; this.dispatch(this.stack[this.index]); }
  }

  forward() {
    if (this.index < this.stack.length - 1) { this.index++; this.dispatch(this.stack[this.index]); }
  }

  private dispatch(hash: string) {
    (globalThis as any).window.location.hash = hash;
    (globalThis as any).window.dispatchEvent(new Event('hashchange'));
  }
}

const historyHarness = new BrowserHistoryHarness();

(globalThis as any).window = {
  localStorage: mockStorage,
  location: { hash: '', replace(h: string) { this.hash = h; } },
  history: historyHarness,
  addEventListener: browserEvents.addEventListener.bind(browserEvents),
  removeEventListener: browserEvents.removeEventListener.bind(browserEvents),
  dispatchEvent: browserEvents.dispatchEvent.bind(browserEvents),
};

import { Router } from '../src/router/router.ts';
import { AuthService } from '../src/auth/auth-service.ts';
import { registerAuthGuard } from '../src/router/auth-guard.ts';

describe('Router & Deep-Link Blackbox Tests (US-0066)', () => {
  let router: Router;
  let unlistenGuard: (() => void) | null = null;
  let auth: AuthService;

  beforeEach(() => {
    mockStorage.clear();
    router = new Router();
    router.reset();
    auth = new AuthService();
    historyHarness.stack = [];
    historyHarness.index = -1;
    (globalThis as any).window.location.hash = '';
  });

  afterEach(() => {
    unlistenGuard?.();
    router.stop();
  });

  it('matches hash paths and extracts parameters for deep links', () => {
    const rootMatch = router.match('#/campaigns');
    assert.ok(rootMatch);
    assert.equal(rootMatch.path, '#/campaigns');
    assert.equal(rootMatch.pattern, '#/campaigns');

    const deepLink = router.match('#/campaigns/42/sessions/108');
    assert.ok(deepLink);
    assert.equal(deepLink.pattern, '#/campaigns/:campaignId/sessions/:sessionId');
    assert.equal(deepLink.params.campaignId, '42');
    assert.equal(deepLink.params.sessionId, '108');

    // Breadcrumbs resolution
    assert.ok(deepLink.breadcrumbs.length >= 2);
    assert.equal(deepLink.breadcrumbs[0].label, 'Campaigns');
    assert.equal(deepLink.breadcrumbs[0].path, '#/campaigns');
  });

  it('verifies browser history navigation with forward and back hash changes', async () => {
    router.start();

    // 1. Visitor navigates to #/campaigns
    historyHarness.navigate('#/campaigns');
    await router.navigate('#/campaigns');
    assert.equal((globalThis as any).window.location.hash, '#/campaigns');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');

    // 2. Visitor deep-links into active session
    historyHarness.navigate('#/campaigns/42/sessions/108');
    await router.navigate('#/campaigns/42/sessions/108');
    assert.equal((globalThis as any).window.location.hash, '#/campaigns/42/sessions/108');
    assert.equal(router.getCurrentRoute()?.params.campaignId, '42');
    assert.equal(router.getCurrentRoute()?.params.sessionId, '108');

    // 3. Browser Back button triggered
    historyHarness.back();
    await router.navigate((globalThis as any).window.location.hash);
    assert.equal((globalThis as any).window.location.hash, '#/campaigns');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');

    // 4. Browser Forward button triggered
    historyHarness.forward();
    await router.navigate((globalThis as any).window.location.hash);
    assert.equal((globalThis as any).window.location.hash, '#/campaigns/42/sessions/108');
    assert.equal(router.getCurrentRoute()?.params.sessionId, '108');
  });

  it('executes route teardown when navigating away from an active session', async () => {
    let wsClosed = false;
    let audioDisposed = false;

    await router.navigate('#/campaigns/42/sessions/108');
    router.registerTeardown(() => { wsClosed = true; });
    router.registerTeardown(() => { audioDisposed = true; });

    assert.equal(wsClosed, false);
    assert.equal(audioDisposed, false);

    // Navigate to campaign hub
    await router.navigate('#/campaigns');
    assert.equal(wsClosed, true);
    assert.equal(audioDisposed, true);
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');
  });
});

describe('Auth Guard & Session Persistence Tests (US-0062)', () => {
  let router: Router;
  let auth: AuthService;
  let unlistenGuard: (() => void) | null = null;

  beforeEach(() => {
    mockStorage.clear();
    router = new Router();
    router.reset();
    auth = new AuthService();
    unlistenGuard = registerAuthGuard(router, auth);
  });

  afterEach(() => {
    unlistenGuard?.();
    router.stop();
  });

  it('redirects unauthenticated visitor visiting protected route to #/login', async () => {
    assert.equal(auth.isAuthenticated(), false);

    const navigated = await router.navigate('#/campaigns');
    assert.equal(navigated, true);
    assert.equal(router.getCurrentRoute()?.path, '#/login');
    assert.equal((globalThis as any).window.location.hash, '#/login');
  });

  it('permits direct access to protected routes when valid session exists in localStorage', async () => {
    // 1. Sign in via public login frontdoor
    await auth.login('Marcus', 'Password123!');
    assert.equal(auth.isAuthenticated(), true);

    // Verify session in localStorage
    const rawSession = mockStorage.getItem('rf_auth_session');
    assert.ok(rawSession);
    assert.equal(JSON.parse(rawSession).user.username, 'Marcus');

    // 2. Access protected route directly
    const navigated = await router.navigate('#/campaigns/42/sessions/108');
    assert.equal(navigated, true);
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns/42/sessions/108');
    assert.equal(router.getCurrentRoute()?.params.sessionId, '108');
  });

  it('restores authenticated session upon browser reload and allows protected navigation', async () => {
    await auth.login('EvelynDM', 'VaultPass123!');

    // Simulate browser reload with new AuthService instance
    const freshAuth = new AuthService();
    assert.equal(freshAuth.isAuthenticated(), true);
    assert.equal(freshAuth.getUser()?.username, 'EvelynDM');

    const freshRouter = new Router();
    const cleanup = registerAuthGuard(freshRouter, freshAuth);

    const allowed = await freshRouter.navigate('#/characters');
    assert.equal(allowed, true);
    assert.equal(freshRouter.getCurrentRoute()?.path, '#/characters');

    cleanup();
  });

  it('triggers redirection to login when token is cleared or expired', async () => {
    await auth.login('SarahCleric', 'SecretKey456!');
    await router.navigate('#/campaigns');
    assert.equal(router.getCurrentRoute()?.path, '#/campaigns');

    // User logs out or token expires -> clears session
    auth.logout();
    assert.equal(auth.isAuthenticated(), false);
    assert.equal(mockStorage.getItem('rf_auth_session'), null);

    // Allow async route navigation triggered by auth change to settle
    await new Promise((resolve) => setTimeout(resolve, 10));

    // Guard reacts to auth change and redirects to #/login
    assert.equal(router.getCurrentRoute()?.path, '#/login');
    assert.equal((globalThis as any).window.location.hash, '#/login');

    // Subsequent attempts to visit protected route redirect to login
    await router.navigate('#/campaigns/42');
    assert.equal(router.getCurrentRoute()?.path, '#/login');
  });
});
