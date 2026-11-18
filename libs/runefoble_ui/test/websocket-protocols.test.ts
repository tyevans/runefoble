import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { websocketProtocols } from '../src/index.ts';

describe('websocketProtocols', () => {
  it('returns the version protocol and the bearer protocol for a token', () => {
    assert.deepEqual(websocketProtocols('abc.def.ghi'), ['runefoble.v1', 'runefoble.bearer.abc.def.ghi']);
  });

  it('refuses to build a list without a token', () => {
    assert.throws(() => websocketProtocols(''), /signed-in access token/);
  });
});
