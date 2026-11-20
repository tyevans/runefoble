/**
 * Unit tests for lobby readiness counting. TASK-0870.
 *
 * Owner and DM roles coordinate the session and are never counted as players.
 * With no player in the session, the summary shows zero players.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { computeReadinessSummary } from '../src/lobby/types.ts';
import type { LobbyParticipant } from '../src/lobby/types.ts';

function participant(overrides: Partial<LobbyParticipant> & Pick<LobbyParticipant, 'userId' | 'role'>): LobbyParticipant {
  return {
    username: overrides.userId,
    isReady: false,
    isAbsent: false,
    ...overrides,
  };
}

describe('computeReadinessSummary', () => {
  it('shows zero players when only a DM is present', () => {
    const summary = computeReadinessSummary([participant({ userId: 'dm-1', role: 'dm' })]);

    assert.equal(summary.totalActivePlayers, 0);
    assert.equal(summary.readyCount, 0);
    assert.equal(summary.summaryText, 'No players have joined');
    assert.equal(summary.allReady, false);
  });

  it('shows zero players when only the owner and a spectator are present', () => {
    const summary = computeReadinessSummary([
      participant({ userId: 'owner-1', role: 'owner' }),
      participant({ userId: 'watcher-1', role: 'spectator' }),
    ]);

    assert.equal(summary.summaryText, 'No players have joined');
  });

  it('counts a ready player and leaves coordinators out of the total', () => {
    const summary = computeReadinessSummary([
      participant({ userId: 'dm-1', role: 'dungeon_master' }),
      participant({ userId: 'p-1', role: 'player', isReady: true }),
      participant({ userId: 'p-2', role: 'player', isReady: false }),
    ]);

    assert.equal(summary.readyCount, 1);
    assert.equal(summary.totalActivePlayers, 2);
    assert.equal(summary.summaryText, '1 of 2 players ready');
    assert.equal(summary.allReady, false);
  });

  it('counts the active players who are not ready and leaves out stand-ins', () => {
    const summary = computeReadinessSummary([
      participant({ userId: 'p-1', role: 'player', isReady: true }),
      participant({ userId: 'p-2', role: 'player', isReady: false }),
      participant({ userId: 'p-3', role: 'player', isReady: false, isAbsent: true }),
    ]);

    assert.equal(summary.notReadyCount, 1);
  });

  it('reports absent stand-ins in the summary text', () => {
    const summary = computeReadinessSummary([
      participant({ userId: 'p-1', role: 'player', isReady: true }),
      participant({ userId: 'p-2', role: 'player', isAbsent: true }),
    ]);

    assert.equal(summary.absentCount, 1);
    assert.equal(summary.summaryText, '1 of 2 players ready, 1 absent stand-in');
  });
});
