/**
 * Fake Zitadel identity provider for frontend unit and blackbox tests (TASK-0524).
 * It stands in for the external IdP only. The App Shell code under test runs unchanged:
 * discovery, PKCE challenge, state and nonce checks, code exchange, refresh, and end session.
 */

import { AuthService, type AuthEnvironment, type UserClaims } from '../../src/auth/auth-service.ts';
import { OidcClient, type FetchLike } from '../../src/auth/oidc-client.ts';
import { s256Challenge, type KeyValueStore } from '../../src/auth/pkce.ts';
import type { RuntimeConfig } from '../../src/auth/runtime-config.ts';

export const TEST_RUNTIME_CONFIG: RuntimeConfig = {
  issuer: 'http://auth.localhost',
  clientId: 'runefoble-web-test',
  scopes: ['openid', 'profile', 'email', 'offline_access'],
  providerName: 'Zitadel',
};

export const TEST_CALLBACK_URI = 'http://app.localhost/auth/callback';
export const TEST_POST_LOGOUT_URI = 'http://app.localhost/';
const ISSUER = TEST_RUNTIME_CONFIG.issuer;

export const DISCOVERY = {
  issuer: ISSUER,
  authorization_endpoint: `${ISSUER}/oauth/v2/authorize`,
  token_endpoint: `${ISSUER}/oauth/v2/token`,
  end_session_endpoint: `${ISSUER}/oidc/v1/end_session`,
};

function base64UrlJson(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** An unsigned JWT-shaped token. The App Shell reads claims only. The server verifies signatures. */
export function fakeJwt(payload: Record<string, unknown>): string {
  return `eyJhbGciOiJSUzI1NiJ9.${base64UrlJson(payload)}.fake-signature`;
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

export interface FakeZitadel {
  env: Partial<AuthEnvironment>;
  navigated: string[];
  tokenRequests: URLSearchParams[];
  endSessionCalls: number;
  /** Lifetime in seconds of the next issued access token. */
  accessTokenLifetime: number;
  /** When true, refresh requests fail with invalid_grant. */
  refreshFails: boolean;
  /** Query string the browser carries back to /auth/callback after a successful login. */
  callbackSearch(): string;
  /** Query string for an IdP error redirect (for example access_denied). */
  errorCallbackSearch(error: string): string;
}

export function createFakeZitadel(options: { username?: string } = {}): FakeZitadel {
  const username = options.username ?? 'marcus';
  const pendingValues = new Map<string, string>();
  const pendingStore: KeyValueStore = {
    getItem: (key) => pendingValues.get(key) ?? null,
    setItem: (key, value) => { pendingValues.set(key, value); },
    removeItem: (key) => { pendingValues.delete(key); },
  };
  const navigated: string[] = [];
  const tokenRequests: URLSearchParams[] = [];
  const fake = { accessTokenLifetime: 3600, refreshFails: false, endSessionCalls: 0 };

  const lastAuthorizeUrl = (): URL => {
    const last = navigated.at(-1);
    if (!last) throw new Error('No authorization request was made.');
    return new URL(last);
  };

  const http: FetchLike = async (input, init) => {
    if (input === `${ISSUER}/.well-known/openid-configuration`) return jsonResponse(200, DISCOVERY);
    if (input === DISCOVERY.token_endpoint) {
      const form = new URLSearchParams(String(init?.body ?? ''));
      tokenRequests.push(form);
      const exp = Math.floor(Date.now() / 1000) + fake.accessTokenLifetime;
      if (form.get('grant_type') === 'refresh_token') {
        if (fake.refreshFails || form.get('refresh_token') !== 'refresh-1') {
          return jsonResponse(400, { error: 'invalid_grant' });
        }
        return jsonResponse(200, { access_token: fakeJwt({ sub: 'user-1', exp }), expires_in: fake.accessTokenLifetime });
      }
      if (form.get('grant_type') !== 'authorization_code' || form.get('code') !== 'good-code') {
        return jsonResponse(400, { error: 'invalid_grant' });
      }
      // The IdP checks PKCE: the verifier must hash to the challenge sent in the authorization request.
      const verifier = form.get('code_verifier') ?? '';
      if ((await s256Challenge(verifier)) !== lastAuthorizeUrl().searchParams.get('code_challenge')) {
        return jsonResponse(400, { error: 'invalid_grant', error_description: 'PKCE verification failed' });
      }
      return jsonResponse(200, {
        access_token: fakeJwt({ sub: 'user-1', exp }),
        id_token: fakeJwt({
          sub: 'user-1',
          preferred_username: username,
          email: `${username}@example.test`,
          nonce: lastAuthorizeUrl().searchParams.get('nonce'),
          'urn:zitadel:iam:org:project:roles': ['player'],
        }),
        refresh_token: 'refresh-1',
        expires_in: fake.accessTokenLifetime,
      });
    }
    return jsonResponse(404, {});
  };

  const env: Partial<AuthEnvironment> = {
    oidc: new OidcClient(async () => TEST_RUNTIME_CONFIG, http),
    callbackUri: () => TEST_CALLBACK_URI,
    postLogoutUri: () => TEST_POST_LOGOUT_URI,
    navigate: (url) => {
      if (url.startsWith(DISCOVERY.end_session_endpoint)) fake.endSessionCalls += 1;
      navigated.push(url);
    },
    pendingStore: () => pendingStore,
  };

  return {
    env,
    navigated,
    tokenRequests,
    get endSessionCalls() { return fake.endSessionCalls; },
    get accessTokenLifetime() { return fake.accessTokenLifetime; },
    set accessTokenLifetime(value: number) { fake.accessTokenLifetime = value; },
    get refreshFails() { return fake.refreshFails; },
    set refreshFails(value: boolean) { fake.refreshFails = value; },
    callbackSearch: () => {
      const state = lastAuthorizeUrl().searchParams.get('state') ?? '';
      return `?code=good-code&state=${encodeURIComponent(state)}`;
    },
    errorCallbackSearch: (error) => {
      const state = lastAuthorizeUrl().searchParams.get('state') ?? '';
      return `?error=${encodeURIComponent(error)}&state=${encodeURIComponent(state)}`;
    },
  };
}

/** Runs the real sign-in path against the fake IdP: startSignIn, then the browser returns to the callback. */
export async function signInWithFake(auth: AuthService, fake: FakeZitadel): Promise<UserClaims> {
  await auth.startSignIn();
  return auth.completeSignIn(fake.callbackSearch());
}
