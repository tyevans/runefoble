/**
 * Types and interfaces for Game Session Pre-Game Lobby and Readiness microfrontend.
 * TASK-0212: Game Session Lobby and Readiness Microfrontend
 * Governed by ADR-0004, ADR-0012, ADR-0013.
 */

import { isCoordinatorRole, isSpectatorRole } from './roles.ts';

export interface LobbyCharacterOption {
  id: string;
  name: string;
  characterClass: string;
  level: number;
  portraitUrl?: string | null;
}

export interface LobbyParticipant {
  userId: string;
  username: string;
  avatarUrl?: string | null;
  role: 'owner' | 'dungeon_master' | 'dm' | 'player' | 'spectator' | string;
  onlineStatus?: 'online' | 'idle' | 'offline' | string;
  isReady: boolean;
  isAbsent: boolean;
  characterId?: string | null;
  characterName?: string | null;
  characterClass?: string | null;
  characterLevel?: number;
  portraitUrl?: string | null;
}

export interface ReadinessSummary {
  readyCount: number;
  totalActivePlayers: number;
  absentCount: number;
  /** Active players who are not ready. A stand-in is not counted: the AI plays that seat (TASK-0952). */
  notReadyCount: number;
  allReady: boolean;
  summaryText: string;
}

export interface SelectCharacterEventDetail {
  sessionId: string;
  userId: string;
  characterId: string;
  character?: LobbyCharacterOption;
}

export interface ToggleReadinessEventDetail {
  sessionId: string;
  userId: string;
  isReady: boolean;
}

export interface ToggleStandInEventDetail {
  sessionId: string;
  userId: string;
  isAbsent: boolean;
}

/** Detail of `take-seat`: the caller takes a lobby seat with one character (TASK-0889). */
export interface TakeSeatEventDetail {
  sessionId: string;
  characterId: string;
  characterName: string;
  characterClass: string;
}

export interface LaunchSessionEventDetail {
  sessionId: string;
  campaignId?: string;
}

/**
 * Computes readiness metrics across session participants.
 * Non-spectator, non-coordinator participants are players. Owner and DM roles coordinate
 * the session and are never counted as players (TASK-0870).
 * - Active players: isAbsent == false
 * - Ready players: isAbsent == false && isReady == true
 * - Stand-in players: isAbsent == true
 * - Seats not ready: isAbsent == false && isReady == false
 * With no player present, the summary reports zero players.
 */
export function computeReadinessSummary(participants: LobbyParticipant[]): ReadinessSummary {
  const players = participants.filter((p) => !isSpectatorRole(p.role) && !isCoordinatorRole(p.role));

  const absentList = players.filter((p) => p.isAbsent);
  const activeList = players.filter((p) => !p.isAbsent);
  const readyList = activeList.filter((p) => p.isReady);

  const readyCount = readyList.length;
  const totalActivePlayers = activeList.length;
  const notReadyCount = totalActivePlayers - readyCount;
  const absentCount = absentList.length;
  const totalPlayers = players.length;

  const allReady = totalActivePlayers > 0 && readyCount === totalActivePlayers;

  let summaryText = '';
  if (totalPlayers === 0) {
    summaryText = 'No players have joined';
  } else if (absentCount > 0) {
    const standInPlural = absentCount === 1 ? '1 absent stand-in' : `${absentCount} absent stand-ins`;
    summaryText = `${readyCount} of ${totalPlayers} players ready, ${standInPlural}`;
  } else {
    summaryText = `${readyCount} of ${totalPlayers} players ready`;
  }

  return {
    readyCount,
    totalActivePlayers,
    absentCount,
    notReadyCount,
    allReady,
    summaryText,
  };
}
