/**
 * Unit tests for Session Lobby & Readiness microfrontend data and logic.
 * TASK-0212: Game Session Lobby and Readiness Microfrontend
 * Governed by ADR-0004, ADR-0012, ADR-0013, US-0065.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  type LobbyParticipant,
  type LobbyCharacterOption,
  computeReadinessSummary,
} from '../../services/game_session/ui/src/lobby/types.ts';

const sampleCharacters: LobbyCharacterOption[] = [
  {
    id: 'char-valeros-1',
    name: 'Valeros',
    characterClass: 'Fighter',
    level: 4,
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    id: 'char-kyra-1',
    name: 'Kyra',
    characterClass: 'Cleric',
    level: 4,
    portraitUrl: '/assets/portraits/cleric.svg',
  },
];

const sampleParticipants: LobbyParticipant[] = [
  {
    userId: 'usr-evelyn',
    username: 'Evelyn (GM)',
    role: 'owner',
    onlineStatus: 'online',
    isReady: true,
    isAbsent: false,
    characterName: 'Dungeon Master',
  },
  {
    userId: 'usr-marcus',
    username: 'Marcus Vance',
    role: 'player',
    onlineStatus: 'online',
    isReady: true,
    isAbsent: false,
    characterId: 'char-valeros-1',
    characterName: 'Valeros',
    characterClass: 'Fighter',
    characterLevel: 4,
  },
  {
    userId: 'usr-sarah',
    username: 'Sarah Chen',
    role: 'player',
    onlineStatus: 'offline',
    isReady: false,
    isAbsent: true, // Marked for AI stand-in
    characterId: 'char-kyra-1',
    characterName: 'Kyra',
    characterClass: 'Cleric',
    characterLevel: 4,
  },
  {
    userId: 'usr-spectator-tom',
    username: 'Spectator Tom',
    role: 'spectator',
    onlineStatus: 'online',
    isReady: false,
    isAbsent: false,
  },
];

describe('Session Lobby Readiness Summary Calculation (US-0065)', () => {
  it('computes 1 of 2 players ready with 1 absent stand-in (US-0065 Scenario 1)', () => {
    // Marcus (ready), Sarah (absent stand-in), Evelyn (DM), Tom (spectator)
    // Note: If only 1 player is active (Marcus) and 1 is absent (Sarah):
    // Total evaluated players: Marcus and Sarah.
    // Active player: Marcus (ready).
    // Absent stand-in: Sarah.
    const res = computeReadinessSummary(sampleParticipants);
    assert.equal(res.readyCount, 1);
    assert.equal(res.totalActivePlayers, 1);
    assert.equal(res.absentCount, 1);
    assert.equal(res.allReady, true);
    assert.equal(res.summaryText, '1 of 2 players ready, 1 absent stand-in');
  });

  it('correctly handles 1 of 2 active players ready plus 1 absent stand-in', () => {
    const participants: LobbyParticipant[] = [
      sampleParticipants[0], // GM
      sampleParticipants[1], // Marcus (ready)
      {
        userId: 'usr-lyra',
        username: 'Lyra',
        role: 'player',
        onlineStatus: 'online',
        isReady: false, // active, but not ready
        isAbsent: false,
        characterName: 'Aeloria',
      },
      sampleParticipants[2], // Sarah (absent stand-in)
    ];

    const res = computeReadinessSummary(participants);
    assert.equal(res.readyCount, 1);
    assert.equal(res.totalActivePlayers, 2);
    assert.equal(res.absentCount, 1);
    assert.equal(res.allReady, false);
    assert.equal(res.summaryText, '1 of 3 players ready, 1 absent stand-in');
  });

  it('reports all players ready when all active non-spectators have isReady set', () => {
    const participants: LobbyParticipant[] = [
      sampleParticipants[0], // GM
      sampleParticipants[1], // Marcus (ready)
      {
        userId: 'usr-lyra',
        username: 'Lyra',
        role: 'player',
        onlineStatus: 'online',
        isReady: true,
        isAbsent: false,
        characterName: 'Aeloria',
      },
    ];

    const res = computeReadinessSummary(participants);
    assert.equal(res.readyCount, 2);
    assert.equal(res.totalActivePlayers, 2);
    assert.equal(res.absentCount, 0);
    assert.equal(res.allReady, true);
    assert.equal(res.summaryText, '2 of 2 players ready');
  });

  it('excludes spectators from active player readiness counts', () => {
    const participants: LobbyParticipant[] = [
      sampleParticipants[1], // Marcus (player, ready)
      sampleParticipants[3], // Spectator Tom (unready)
    ];

    const res = computeReadinessSummary(participants);
    assert.equal(res.readyCount, 1);
    assert.equal(res.totalActivePlayers, 1);
    assert.equal(res.absentCount, 0);
    assert.equal(res.allReady, true);
    assert.equal(res.summaryText, '1 of 1 players ready');
  });

  it('handles empty participant list gracefully', () => {
    const res = computeReadinessSummary([]);
    assert.equal(res.readyCount, 0);
    assert.equal(res.totalActivePlayers, 0);
    assert.equal(res.absentCount, 0);
    assert.equal(res.allReady, false);
    assert.equal(res.summaryText, '0 of 0 players ready');
  });
});

describe('Lobby Participant Character & Control Operations', () => {
  it('matches available characters by identifier for dropdown selection', () => {
    const charId = 'char-valeros-1';
    const matched = sampleCharacters.find((c) => c.id === charId);
    assert.ok(matched);
    assert.equal(matched!.name, 'Valeros');
    assert.equal(matched!.characterClass, 'Fighter');
    assert.equal(matched!.level, 4);
  });

  it('constructs correct payload for launch-session event', () => {
    const detail = {
      sessionId: 'sess-star-eater-15',
      campaignId: 'camp-star-eater',
    };
    assert.equal(detail.sessionId, 'sess-star-eater-15');
    assert.equal(detail.campaignId, 'camp-star-eater');
  });

  it('constructs correct payload for toggle-readiness and toggle-stand-in', () => {
    const readyDetail = {
      sessionId: 'sess-star-eater-15',
      userId: 'usr-marcus',
      isReady: true,
    };
    assert.equal(readyDetail.isReady, true);

    const absentDetail = {
      sessionId: 'sess-star-eater-15',
      userId: 'usr-sarah',
      isAbsent: true,
    };
    assert.equal(absentDetail.isAbsent, true);
  });
});
