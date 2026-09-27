/**
 * Unit tests for Zitadel Browser Authentication Service
 * TASK-0207: Zitadel Auth Client and Login Modal Component
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

describe('Zitadel JWT Claims Extraction & Decoding', () => {
  it('parses valid JWT payloads correctly', () => {
    const payloadObj = {
      sub: 'user-valeros-99',
      preferred_username: 'Valeros',
      email: 'valeros@runefoble.local',
      'urn:zitadel:iam:org:project:roles': ['player', 'dm'],
      exp: 1800000000,
    };
    const encoded = btoa(JSON.stringify(payloadObj));
    const token = `header.${encoded}.signature`;

    const parsed = parseJwtPayload(token);
    assert.ok(parsed);
    assert.equal(parsed.sub, 'user-valeros-99');
    assert.equal(parsed.preferred_username, 'Valeros');

    const claims = extractClaimsFromPayload(parsed);
    assert.equal(claims.user_id, 'user-valeros-99');
    assert.equal(claims.username, 'Valeros');
    assert.equal(claims.email, 'valeros@runefoble.local');
    assert.deepEqual(claims.roles, ['player', 'dm']);
    assert.equal(claims.is_admin, false);
  });

  it('detects admin role correctly from Zitadel claims', () => {
    const payloadObj = {
      sub: 'admin-01',
      preferred_username: 'AdminDM',
      'urn:zitadel:iam:org:project:roles': ['admin', 'dm'],
    };
    const claims = extractClaimsFromPayload(payloadObj);
    assert.equal(claims.is_admin, true);
    assert.deepEqual(claims.roles, ['admin', 'dm']);
  });

  it('handles malformed JWT token gracefully', () => {
    assert.equal(parseJwtPayload('invalid-token'), null);
    assert.equal(parseJwtPayload(''), null);
  });
});

describe('AuthService Login, Storage & Event Flow', () => {
  let auth: AuthService;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    mockStorage.clear();
    auth = new AuthService();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    auth.logout();
  });

  it('starts unauthenticated with clean state', () => {
    assert.equal(auth.isAuthenticated(), false);
    assert.equal(auth.getUser(), null);
    assert.equal(auth.getAccessToken(), null);
  });

  it('exchanges credentials and notifies listeners via event emitter', async () => {
    let notifiedState: AuthState | null = null;
    const unsubscribe = auth.onAuthChanged((state) => {
      notifiedState = state;
    });

    const user = await auth.login('Marcus', 'SuperSecret123!');
    assert.ok(user);
    assert.equal(user.username, 'Marcus');
    assert.equal(auth.isAuthenticated(), true);
    assert.ok(auth.getAccessToken());

    assert.ok(notifiedState);
    assert.equal((notifiedState as AuthState).isAuthenticated, true);
    assert.equal((notifiedState as AuthState).user?.username, 'Marcus');

    unsubscribe();
  });

  it('persists session in localStorage without leaking sensitive password credentials', async () => {
    await auth.login('EvelynDM', 'P@ssword1234');

    const storedRaw = mockStorage.getItem('rf_auth_session');
    assert.ok(storedRaw, 'Storage must have rf_auth_session item');
    const stored = JSON.parse(storedRaw);

    assert.ok(stored.tokens.accessToken);
    assert.ok(stored.user);
    assert.equal(stored.user.username, 'EvelynDM');
    // Ensure sensitive password was never written to storage
    assert.equal((stored.user as any).password, undefined);
    assert.equal(storedRaw.includes('P@ssword1234'), false);
  });

  it('restores authenticated session from localStorage upon initialization', async () => {
    await auth.login('Sarah', 'MyVaultKey123!');
    assert.equal(auth.isAuthenticated(), true);

    // Instantiate a new AuthService to simulate browser reload
    const freshAuth = new AuthService();
    assert.equal(freshAuth.isAuthenticated(), true);
    assert.equal(freshAuth.getUser()?.username, 'Sarah');
  });

  it('clears session and emits unauthenticated state upon logout', async () => {
    await auth.login('Devon', 'Passw0rdDevon!');
    assert.equal(auth.isAuthenticated(), true);

    let authChangeCount = 0;
    auth.onAuthChanged(() => { authChangeCount++; });

    auth.logout();
    assert.equal(auth.isAuthenticated(), false);
    assert.equal(auth.getUser(), null);
    assert.equal(auth.getAccessToken(), null);
    assert.equal(mockStorage.getItem('rf_auth_session'), null);
    assert.ok(authChangeCount > 0);
  });

  it('performs silent token refresh successfully', async () => {
    await auth.login('Alex', 'AlexToken1234');
    const originalToken = auth.getAccessToken();
    assert.ok(originalToken);

    // Call frontdoor refreshToken
    const refreshedToken = await auth.refreshToken();
    assert.ok(refreshedToken);
    assert.equal(auth.isAuthenticated(), true);
  });

  it('handles user registration and creates active session', async () => {
    const user = await auth.register('NewAdventurer', 'adventurer@runefoble.local', 'PassKey123456');
    assert.ok(user);
    assert.equal(user.username, 'NewAdventurer');
    assert.equal(user.email, 'adventurer@runefoble.local');
    assert.equal(auth.isAuthenticated(), true);
  });

  it('handles backend token response with real API mock', async () => {
    const mockTokenPayload = {
      sub: 'remote-user-77',
      preferred_username: 'RemoteWizard',
      email: 'wizard@runefoble.com',
      roles: ['dm'],
    };
    const fakeJwt = `mock.${btoa(JSON.stringify(mockTokenPayload))}.sig`;

    globalThis.fetch = async (url: any) => {
      if (String(url).endsWith('/token')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            access_token: fakeJwt,
            refresh_token: 'refresh-token-xyz',
            expires_in: 7200,
          }),
        } as any;
      }
      return { ok: false, status: 404 } as any;
    };

    auth.devFallback = false;
    const user = await auth.login('RemoteWizard', 'RemotePassword!');
    assert.equal(user.user_id, 'remote-user-77');
    assert.equal(user.username, 'RemoteWizard');
    assert.equal(user.email, 'wizard@runefoble.com');
    assert.deepEqual(user.roles, ['dm']);
    assert.equal(auth.getAccessToken(), fakeJwt);
  });
});
