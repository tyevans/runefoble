/**
 * Unit tests for the game session role normalizer. TASK-0870.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { isCoordinatorRole, isSpectatorRole, normalizeRole } from '../src/lobby/roles.ts';

describe('normalizeRole', () => {
  it('maps the dm alias and the dungeon_master name to the same role', () => {
    assert.equal(normalizeRole('dm'), 'dungeon_master');
    assert.equal(normalizeRole('dungeon_master'), 'dungeon_master');
  });

  it('ignores case and surrounding space', () => {
    assert.equal(normalizeRole('  Owner '), 'owner');
    assert.equal(normalizeRole('SPECTATOR'), 'spectator');
  });

  it('returns unknown for empty, missing and unrecognised roles', () => {
    assert.equal(normalizeRole(''), 'unknown');
    assert.equal(normalizeRole(null), 'unknown');
    assert.equal(normalizeRole(undefined), 'unknown');
    assert.equal(normalizeRole('admin'), 'unknown');
  });
});

describe('role classification', () => {
  it('treats owner and every DM alias as coordinators', () => {
    assert.equal(isCoordinatorRole('owner'), true);
    assert.equal(isCoordinatorRole('dm'), true);
    assert.equal(isCoordinatorRole('dungeon_master'), true);
    assert.equal(isCoordinatorRole('player'), false);
    assert.equal(isCoordinatorRole('spectator'), false);
  });

  it('identifies spectators only', () => {
    assert.equal(isSpectatorRole('spectator'), true);
    assert.equal(isSpectatorRole('player'), false);
  });
});
