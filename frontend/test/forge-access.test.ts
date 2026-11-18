/**
 * Asset Forge access in the App Shell (TASK-0645). Only `permissions.manage` opens the forge.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveForgeAccess } from '../src/views/forge-access.ts';

describe('resolveForgeAccess', () => {
  it('allows the forge when the campaign reports permissions.manage', () => {
    assert.equal(resolveForgeAccess({ manage: true }), 'allowed');
  });

  it('denies the forge when the campaign reports permissions.manage as false', () => {
    assert.equal(resolveForgeAccess({ manage: false }), 'denied');
  });

  it('denies the forge when the campaign has no permissions yet', () => {
    assert.equal(resolveForgeAccess(undefined), 'denied');
    assert.equal(resolveForgeAccess(null), 'denied');
    assert.equal(resolveForgeAccess({}), 'denied');
  });
});
