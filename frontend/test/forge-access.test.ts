/**
 * Asset Forge access in the App Shell (TASK-0645, TASK-0559). Only the `manage` capability opens the forge.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveForgeAccess } from '../src/views/forge-access.ts';

describe('resolveForgeAccess', () => {
  it('allows the forge when the caller holds the manage capability', () => {
    assert.equal(resolveForgeAccess({ manage: true }), 'allowed');
  });

  it('denies the forge when the manage capability is false', () => {
    assert.equal(resolveForgeAccess({ manage: false }), 'denied');
  });

  it('denies the forge when the capabilities have not loaded yet', () => {
    assert.equal(resolveForgeAccess(undefined), 'denied');
    assert.equal(resolveForgeAccess(null), 'denied');
    assert.equal(resolveForgeAccess({}), 'denied');
  });
});
