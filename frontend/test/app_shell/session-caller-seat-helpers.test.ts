/**
 * The caller seat lookup (TASK-0974). A seat counts only for the caller who holds it.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { findCallerSeat } from '../../src/app/active-character.ts';

const SEATS = [
  { userId: 'user-alice', characterId: 'char-valeros', characterName: 'Valeros', isStandInActive: true },
  { userId: 'user-bob', characterId: 'char-kyra', characterName: 'Kyra', isStandInActive: false },
];

describe('findCallerSeat', () => {
  it('returns the seat that the caller holds', () => {
    assert.equal(findCallerSeat(SEATS, 'user-alice')?.characterId, 'char-valeros');
  });

  it('returns null for a caller with no seat', () => {
    assert.equal(findCallerSeat(SEATS, 'user-carol'), null);
  });

  it('returns null for an unknown caller id', () => {
    assert.equal(findCallerSeat(SEATS, ''), null);
  });
});
