/**
 * The join path survives Zitadel sign-in (ADR-0023 e, TASK-0950).
 * Only a join route path is stored, and the key is removed when it is read.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  POST_SIGN_IN_PATH_KEY,
  isJoinRoutePath,
  savePostSignInPath,
  takePostSignInPath,
  type PathStore,
} from '../src/app/post-sign-in-path.ts';

function memoryStore(): PathStore & { map: Map<string, string> } {
  const map = new Map<string, string>();
  return {
    map,
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => { map.set(key, value); },
    removeItem: (key) => { map.delete(key); },
  };
}

describe('post sign-in path', () => {
  it('recognises only a join route path with one token segment', () => {
    assert.equal(isJoinRoutePath('#/join/abc-123'), true);
    assert.equal(isJoinRoutePath('#/join/'), false);
    assert.equal(isJoinRoutePath('#/join/a/b'), false);
    assert.equal(isJoinRoutePath('#/join/a?x=1'), false);
    assert.equal(isJoinRoutePath('#/campaigns'), false);
  });

  it('stores a join path and returns it once, then removes the key', () => {
    const store = memoryStore();
    savePostSignInPath(store, '#/join/tok-1');
    assert.equal(store.map.get(POST_SIGN_IN_PATH_KEY), '#/join/tok-1');
    assert.equal(takePostSignInPath(store), '#/join/tok-1');
    assert.equal(store.map.has(POST_SIGN_IN_PATH_KEY), false);
    assert.equal(takePostSignInPath(store), null);
  });

  it('ignores any path that is not a join route', () => {
    const store = memoryStore();
    savePostSignInPath(store, '#/campaigns/c1');
    assert.equal(store.map.has(POST_SIGN_IN_PATH_KEY), false);
  });

  it('never returns a stored value that is not a join route, and still removes it', () => {
    const store = memoryStore();
    store.map.set(POST_SIGN_IN_PATH_KEY, 'https://evil.example/#/join/x');
    assert.equal(takePostSignInPath(store), null);
    assert.equal(store.map.has(POST_SIGN_IN_PATH_KEY), false);
  });
});
