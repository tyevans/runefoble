import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { authHeaders, wsProtocols, type TokenSource } from '../src/auth/transport.ts';

function source(token: string | null): TokenSource {
  return { getAccessToken: () => token };
}

describe('authHeaders', () => {
  it('sends the bearer token and no identity header', () => {
    assert.deepEqual(authHeaders(source('tok-1')), { Authorization: 'Bearer tok-1' });
  });

  it('sends no headers when nobody is signed in', () => {
    assert.deepEqual(authHeaders(source(null)), {});
  });
});

describe('wsProtocols', () => {
  it('offers the version and bearer subprotocols', () => {
    assert.deepEqual(wsProtocols(source('tok-1')), ['runefoble.v1', 'runefoble.bearer.tok-1']);
  });

  it('returns null when nobody is signed in, so the socket is not opened', () => {
    assert.equal(wsProtocols(source(null)), null);
  });
});
