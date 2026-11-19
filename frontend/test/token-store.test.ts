/**
 * Unit tests for the App Shell session record in localStorage (TASK-0871).
 * The record key `rf_auth_session` is a contract with the e2e suite (TASK-0525). Do not rename it.
 */

import { afterEach, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  loadStoredSession,
  removeStoredSession,
  saveStoredSession,
  STORAGE_KEY,
} from '../src/auth/token-store.ts';

class MemoryStorage {
  private data = new Map<string, string>();
  getItem(key: string): string | null { return this.data.get(key) ?? null; }
  setItem(key: string, value: string): void { this.data.set(key, String(value)); }
  removeItem(key: string): void { this.data.delete(key); }
}

const tokens = { accessToken: 'access-fixture', idToken: 'id-fixture', refreshToken: 'refresh-fixture', expiresAt: 4_102_444_800_000 };
const user = { user_id: 'user-1', username: 'marcus', roles: ['player'] };

let storage: MemoryStorage;
let previousWindow: unknown;

beforeEach(() => {
  previousWindow = (globalThis as { window?: unknown }).window;
  storage = new MemoryStorage();
  (globalThis as { window?: unknown }).window = { localStorage: storage };
});

afterEach(() => {
  (globalThis as { window?: unknown }).window = previousWindow;
});

describe('token store (TASK-0871)', () => {
  it('keeps the storage key that the e2e suite reads', () => {
    assert.equal(STORAGE_KEY, 'rf_auth_session');
  });

  it('saves tokens and user under the storage key and loads them back', () => {
    saveStoredSession(tokens, user);
    assert.deepEqual(JSON.parse(storage.getItem('rf_auth_session') ?? 'null'), { tokens, user });
    assert.deepEqual(loadStoredSession(), { tokens, user });
  });

  it('returns null when no record exists', () => {
    assert.equal(loadStoredSession(), null);
  });

  it('returns null for a record that lacks an access token or a user', () => {
    storage.setItem('rf_auth_session', JSON.stringify({ tokens: { expiresAt: 1 }, user }));
    assert.equal(loadStoredSession(), null);
    storage.setItem('rf_auth_session', JSON.stringify({ tokens }));
    assert.equal(loadStoredSession(), null);
    storage.setItem('rf_auth_session', 'null');
    assert.equal(loadStoredSession(), null);
  });

  it('throws when the stored record is not JSON', () => {
    storage.setItem('rf_auth_session', '{not json');
    assert.throws(() => loadStoredSession(), SyntaxError);
  });

  it('removes the record', () => {
    saveStoredSession(tokens, user);
    removeStoredSession();
    assert.equal(storage.getItem('rf_auth_session'), null);
    assert.equal(loadStoredSession(), null);
  });

  it('does nothing and reports no session when storage is unavailable', () => {
    (globalThis as { window?: unknown }).window = undefined;
    assert.doesNotThrow(() => saveStoredSession(tokens, user));
    assert.doesNotThrow(() => removeStoredSession());
    assert.equal(loadStoredSession(), null);
  });

  it('does not throw when the browser refuses to write storage', () => {
    (globalThis as { window?: unknown }).window = {
      localStorage: {
        getItem: () => null,
        setItem: () => { throw new Error('QuotaExceededError'); },
        removeItem: () => { throw new Error('SecurityError'); },
      },
    };
    assert.doesNotThrow(() => saveStoredSession(tokens, user));
    assert.doesNotThrow(() => removeStoredSession());
  });
});
