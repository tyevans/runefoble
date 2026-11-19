/**
 * Unit tests for the lobby seat offer. TASK-0889.
 *
 * The offer reads the capability flags that the server returns. It never reads a role label.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { canTakeSeat } from '../src/lobby/seat.ts';
import type { LobbyParticipant } from '../src/lobby/types.ts';

const seated: LobbyParticipant = {
  userId: 'player-mira',
  username: 'Mira',
  role: 'player',
  isReady: false,
  isAbsent: false,
};

describe('canTakeSeat', () => {
  it('offers a seat to a caller who can play and is not seated', () => {
    assert.equal(canTakeSeat({ canPlay: true, canRunSession: false, currentUserId: 'player-mira', participants: [] }), true);
  });

  it('does not offer a seat to a caller who already has one', () => {
    assert.equal(canTakeSeat({ canPlay: true, canRunSession: false, currentUserId: 'player-mira', participants: [seated] }), false);
  });

  it('does not offer a seat to the person who runs the session', () => {
    assert.equal(canTakeSeat({ canPlay: true, canRunSession: true, currentUserId: 'dm-evelyn', participants: [] }), false);
  });

  it('does not offer a seat to a caller without the play capability', () => {
    assert.equal(canTakeSeat({ canPlay: false, canRunSession: false, currentUserId: 'spectator-tom', participants: [] }), false);
  });

  it('does not offer a seat before the caller is known', () => {
    assert.equal(canTakeSeat({ canPlay: true, canRunSession: false, currentUserId: '', participants: [] }), false);
  });
});
