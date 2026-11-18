/**
 * Unit tests for Zitadel Browser Authentication Service
 * TASK-0207: Zitadel Auth Client and Login Modal Component
 * TASK-0524: Authorization code with PKCE against Zitadel
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

// Set up browser-like environment in Node if needed
class MockLocalStorage {
  private data = new Map<string, string>();
  getItem(key: string): string | null { return this.data.get(key) ?? null; }
  setItem(key: string, val: string): void { this.data.set(key, String(val)); }
  removeItem(key: string): void { this.data.delete(key); }
  clear(): void { this.data.clear(); }
}

const mockStorage = new MockLocalStorage();
const eventTarget = new EventTarget();

if (typeof (globalThis as any).window === 'undefined') {
  (globalThis as any).window = {
    localStorage: mockStorage,
    addEventListener: eventTarget.addEventListener.bind(eventTarget),
    removeEventListener: eventTarget.removeEventListener.bind(eventTarget),
    dispatchEvent: eventTarget.dispatchEvent.bind(eventTarget),
    location: { hash: '', replace(h: string) { this.hash = h; } },
  };
} else {
  (globalThis as any).window.localStorage = mockStorage;
}

import {
  AuthService,
  parseJwtPayload,
  extractClaimsFromPayload,
  type AuthState,
} from '../src/auth/auth-service.ts';
import { createFakeZitadel, signInWithFake, type FakeZitadel } from './support/fake-zitadel.ts';

describe('Zitadel JWT Claims Extraction & Decoding', () => {
  it('parses valid JWT payloads correctly', () => {
    const payloadObj = {
      sub: 'user-fixture-99',
      preferred_username: 'Valeros',
      email: 'valeros@runefoble.local',
      'urn:zitadel:iam:org:project:roles': ['player', 'dm'],
      exp: 1800000000,
    };
    const encoded = btoa(JSON.stringify(payloadObj));
    const token = `header.${encoded}.signature`;

    const parsed = parseJwtPayload(token);
    assert.ok(parsed);
    assert.equal(parsed.sub, 'user-fixture-99');
    assert.equal(parsed.preferred_username, 'Valeros');

    const claims = extractClaimsFromPayload(parsed);
    assert.equal(claims.user_id, 'user-fixture-99');
    assert.equal(claims.username, 'Valeros');
    assert.equal(claims.email, 'valeros@runefoble.local');
    assert.deepEqual(claims.roles, ['player', 'dm']);
  });

  it('keeps role names as display data and derives no admin flag from them', () => {
    const payloadObj = {
      sub: 'admin-01',
      preferred_username: 'AdminDM',
      'urn:zitadel:iam:org:project:roles': ['admin', 'dm'],
    };
    const claims = extractClaimsFromPayload(payloadObj);
    assert.deepEqual(claims.roles, ['admin', 'dm']);
    assert.equal('is_admin' in claims, false);
  });

  it('handles malformed JWT token gracefully', () => {
    assert.equal(parseJwtPayload('invalid-token'), null);
    assert.equal(parseJwtPayload(''), null);
  });
});

describe('AuthService OIDC Authorization Code with PKCE (TASK-0524)', () => {
  let auth: AuthService;
  let fake: FakeZitadel;

  beforeEach(() => {
    mockStorage.clear();
    fake = createFakeZitadel();
    auth = new AuthService(fake.env);
  });

  afterEach(() => {
    mockStorage.clear();
  });

  it('starts unauthenticated with clean state', () => {
    assert.equal(auth.isAuthenticated(), false);
    assert.equal(auth.getUser(), null);
    assert.equal(auth.getAccessToken(), null);
  });

  it('redirects to the Zitadel authorize endpoint with PKCE, state, and nonce and no password', async () => {
    await auth.startSignIn();

    assert.equal(fake.navigated.length, 1);
    const url = new URL(fake.navigated[0]);
    assert.equal(url.origin + url.pathname, 'http://auth.localhost/oauth/v2/authorize');
    assert.equal(url.searchParams.get('response_type'), 'code');
    assert.equal(url.searchParams.get('client_id'), 'runefoble-web-test');
    assert.equal(url.searchParams.get('redirect_uri'), 'http://app.localhost/auth/callback');
    assert.equal(url.searchParams.get('code_challenge_method'), 'S256');
    assert.ok((url.searchParams.get('code_challenge') ?? '').length >= 43);
    assert.ok((url.searchParams.get('state') ?? '').length > 0);
    assert.ok((url.searchParams.get('nonce') ?? '').length > 0);
    assert.equal(url.searchParams.get('scope'), 'openid profile email offline_access');
    assert.equal(url.searchParams.has('prompt'), false);
    assert.equal(url.searchParams.has('password'), false);
  });

  it('asks Zitadel for the hosted registration page when signing up', async () => {
    await auth.startSignIn({ signUp: true });
    assert.equal(new URL(fake.navigated[0]).searchParams.get('prompt'), 'create');
  });

  it('completes sign-in: exchanges the code with the verifier and stores Zitadel tokens only', async () => {
    let notified = false;
    auth.onAuthChanged(() => { notified = true; });

    const user = await signInWithFake(auth, fake);

    assert.equal(user.username, 'marcus');
    assert.equal(user.email, 'marcus@example.test');
    assert.equal(auth.isAuthenticated(), true);
    assert.equal(auth.getAccessToken() !== null, true);
    assert.equal(notified, true);

    const exchange = fake.tokenRequests.find((f) => f.get('grant_type') === 'authorization_code');
    assert.ok(exchange, 'the code must be exchanged at the token endpoint');
    assert.ok((exchange.get('code_verifier') ?? '').length >= 43);
    assert.equal(exchange.get('client_secret'), null);

    const stored = JSON.parse(mockStorage.getItem('rf_auth_session') ?? 'null');
    assert.equal(stored.user.username, 'marcus');
    assert.ok(stored.tokens.idToken, 'the ID token is kept for logout');
  });

  it('removes the one-time sign-in data after the callback', async () => {
    await signInWithFake(auth, fake);
    await assert.rejects(() => auth.completeSignIn(fake.callbackSearch()), /No sign-in is pending/);
  });

  it('rejects a callback whose state does not match and stores no token', async () => {
    await auth.startSignIn();
    await assert.rejects(
      () => auth.completeSignIn('?code=good-code&state=forged-state'),
      /state did not match/
    );
    assert.equal(auth.isAuthenticated(), false);
    assert.equal(mockStorage.getItem('rf_auth_session'), null);
    assert.equal(fake.tokenRequests.length, 0, 'no code exchange happens for a forged state');
  });

  it('rejects an ID token whose nonce does not match and stores no token', async () => {
    await auth.startSignIn();
    fake.navigated[0] = fake.navigated[0].replace(/nonce=[^&]+/, 'nonce=other-nonce');
    await assert.rejects(() => auth.completeSignIn(fake.callbackSearch()), /nonce did not match/);
    assert.equal(auth.isAuthenticated(), false);
  });

  it('shows the IdP error and stores no token when the user cancels at Zitadel', async () => {
    await auth.startSignIn();
    await assert.rejects(
      () => auth.completeSignIn(fake.errorCallbackSearch('access_denied')),
      /access_denied/
    );
    assert.equal(auth.isAuthenticated(), false);
  });

  it('persists the session in localStorage without a password', async () => {
    await signInWithFake(auth, fake);
    const storedRaw = mockStorage.getItem('rf_auth_session');
    assert.ok(storedRaw);
    assert.equal(storedRaw.includes('password'), false);
  });

  it('restores an unexpired session after a reload', async () => {
    await signInWithFake(auth, fake);
    const freshAuth = new AuthService(fake.env);
    assert.equal(freshAuth.isAuthenticated(), true);
    assert.equal(freshAuth.getUser()?.username, 'marcus');
  });

  it('treats an expired access token as no session and renews it before use', async () => {
    mockStorage.setItem('rf_auth_session', JSON.stringify({
      tokens: { accessToken: 'eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjEwMH0.s', expiresAt: 1000, refreshToken: 'refresh-1' },
      user: { user_id: 'user-1', username: 'marcus', roles: [] },
    }));
    const expiredAuth = new AuthService(fake.env);
    assert.equal(expiredAuth.isAuthenticated(), false);
    assert.equal(expiredAuth.getAccessToken(), null);

    await new Promise((resolve) => setTimeout(resolve, 0));
    const renewed = expiredAuth.getAccessToken();
    assert.ok(renewed, 'the stored refresh token renews the session');
    assert.notEqual(renewed, 'eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjEwMH0.s');
  });

  it('renews the access token with the refresh token', async () => {
    await signInWithFake(auth, fake);
    const renewed = await auth.refreshToken();
    assert.ok(renewed);
    assert.equal(auth.getAccessToken(), renewed);
    const refresh = fake.tokenRequests.find((f) => f.get('grant_type') === 'refresh_token');
    assert.equal(refresh?.get('refresh_token'), 'refresh-1');
  });

  it('clears the session and throws when the refresh token is rejected', async () => {
    await signInWithFake(auth, fake);
    fake.refreshFails = true;
    await assert.rejects(() => auth.refreshToken(), /Token request failed \(400\)/);
    assert.equal(auth.isAuthenticated(), false);
    assert.equal(mockStorage.getItem('rf_auth_session'), null);
  });

  it('logout clears tokens and ends the Zitadel session with the ID token hint', async () => {
    await signInWithFake(auth, fake);
    await auth.logout();

    assert.equal(auth.isAuthenticated(), false);
    assert.equal(mockStorage.getItem('rf_auth_session'), null);
    const endSession = fake.navigated.at(-1) ?? '';
    assert.ok(endSession.startsWith('http://auth.localhost/oidc/v1/end_session?'));
    const params = new URL(endSession).searchParams;
    assert.ok((params.get('id_token_hint') ?? '').length > 0);
    assert.equal(params.get('post_logout_redirect_uri'), 'http://app.localhost/');
  });

  it('logout without an ID token clears local state and does not navigate', async () => {
    mockStorage.setItem('rf_auth_session', JSON.stringify({
      tokens: { accessToken: fakeAccessToken(), expiresAt: Date.now() + 60_000 },
      user: { user_id: 'user-1', username: 'marcus', roles: [] },
    }));
    const restored = new AuthService(fake.env);
    await restored.logout();
    assert.equal(restored.isAuthenticated(), false);
    assert.equal(fake.navigated.length, 0);
  });

  it('refuses to update a user when no sign-in exists and never invents one', () => {
    assert.throws(() => auth.updateUser({ bio: 'x' }), /without a sign-in session/);
    assert.equal(auth.getUser(), null);
  });

  it('updates the signed-in user and keeps the tokens', async () => {
    await signInWithFake(auth, fake);
    auth.updateUser({ display_name: 'Marcus the Bold' });
    assert.equal(auth.getUser()?.display_name, 'Marcus the Bold');
    assert.equal(auth.getUser()?.username, 'marcus');
    assert.equal(auth.isAuthenticated(), true);
  });
});

function fakeAccessToken(): string {
  return `eyJhbGciOiJSUzI1NiJ9.${btoa(JSON.stringify({ sub: 'user-1', exp: Math.floor(Date.now() / 1000) + 600 }))}.s`;
}
