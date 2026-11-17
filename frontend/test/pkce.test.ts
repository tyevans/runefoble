/**
 * Unit tests for PKCE helpers and runtime config parsing (TASK-0524).
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  createPkceSession,
  s256Challenge,
  randomToken,
  loadPendingSignIn,
  savePendingSignIn,
  clearPendingSignIn,
  PENDING_SIGN_IN_KEY,
  type KeyValueStore,
} from '../src/auth/pkce.ts';
import { parseRuntimeConfig } from '../src/auth/runtime-config.ts';

function memoryStore(): KeyValueStore & { values: Map<string, string> } {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (k) => values.get(k) ?? null,
    setItem: (k, v) => { values.set(k, v); },
    removeItem: (k) => { values.delete(k); },
  };
}

describe('PKCE helpers (RFC 7636)', () => {
  it('derives the S256 challenge from the RFC 7636 appendix B verifier', async () => {
    const verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk';
    assert.equal(await s256Challenge(verifier), 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM');
  });

  it('creates a verifier of 43 to 128 URL-safe characters with a matching challenge', async () => {
    const session = await createPkceSession();
    assert.ok(session.codeVerifier.length >= 43 && session.codeVerifier.length <= 128);
    assert.match(session.codeVerifier, /^[A-Za-z0-9\-_]+$/);
    assert.equal(session.codeChallenge, await s256Challenge(session.codeVerifier));
    assert.notEqual(session.state, session.nonce);
  });

  it('produces a different verifier, state, and nonce for each attempt', async () => {
    const a = await createPkceSession();
    const b = await createPkceSession();
    assert.notEqual(a.codeVerifier, b.codeVerifier);
    assert.notEqual(a.state, b.state);
    assert.notEqual(a.nonce, b.nonce);
    assert.notEqual(randomToken(32), randomToken(32));
  });
});

describe('Pending sign-in storage', () => {
  it('round-trips the pending sign-in and clears it once', () => {
    const store = memoryStore();
    savePendingSignIn(store, { state: 's1', nonce: 'n1', codeVerifier: 'v1' });
    assert.deepEqual(loadPendingSignIn(store), { state: 's1', nonce: 'n1', codeVerifier: 'v1' });
    clearPendingSignIn(store);
    assert.equal(loadPendingSignIn(store), null);
    assert.equal(store.values.has(PENDING_SIGN_IN_KEY), false);
  });

  it('rejects malformed pending data instead of guessing', () => {
    const store = memoryStore();
    store.setItem(PENDING_SIGN_IN_KEY, JSON.stringify({ state: 's1' }));
    assert.throws(() => loadPendingSignIn(store), /malformed/);
  });
});

describe('Runtime config parsing', () => {
  const valid = {
    issuer: 'http://auth.localhost',
    clientId: 'client-1',
    scopes: ['openid', 'profile', 'email', 'offline_access'],
    providerName: 'Zitadel',
  };

  it('accepts the config rendered by the Helm ConfigMap', () => {
    assert.deepEqual(parseRuntimeConfig(valid), valid);
  });

  it('rejects a missing issuer', () => {
    assert.throws(() => parseRuntimeConfig({ ...valid, issuer: '' }), /no issuer/);
  });

  it('rejects scopes that are not a list of strings', () => {
    assert.throws(() => parseRuntimeConfig({ ...valid, scopes: 'openid' }), /scopes/);
  });

  it('rejects a non-object body', () => {
    assert.throws(() => parseRuntimeConfig(null), /JSON object/);
  });
});
