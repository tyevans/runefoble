/**
 * Recap counts (TASK-0953). Each recap line counts once, by its kind.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { recapCounts, type RecapEntry } from '../src/recap/recap-counts.ts';

describe('recapCounts', () => {
  it('counts nothing for an empty recap', () => {
    assert.deepEqual(recapCounts([]), { diceRolls: 0, tokenMoves: 0, standInActions: 0 });
  });

  it('counts dice rolls, token moves and stand-in actions by their kind', () => {
    const entries: RecapEntry[] = [
      { id: '1', speaker: 'system', text: 'Session started.', source: 'system' },
      { id: '2', speaker: 'Valeros', text: '1d20 = 14', source: 'player', actionType: 'dice_roll' },
      { id: '3', speaker: 'Valeros', text: 'moved to 3,4', source: 'player', actionType: 'board_move' },
      { id: '4', speaker: 'Kyra', text: 'Hold the line!', source: 'stand_in', actionType: 'speech' },
      { id: '5', speaker: 'Sarah', text: '2d6 = 9', source: 'player', actionType: 'dice_roll' },
    ];
    assert.deepEqual(recapCounts(entries), { diceRolls: 2, tokenMoves: 1, standInActions: 1 });
  });
});
