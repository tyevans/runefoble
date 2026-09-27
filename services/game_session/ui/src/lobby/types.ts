/**
 * Types and interfaces for Game Session Pre-Game Lobby and Readiness microfrontend.
 * TASK-0212: Game Session Lobby and Readiness Microfrontend
 * Governed by ADR-0004, ADR-0012, ADR-0013.
 */

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

export interface LaunchSessionEventDetail {
  sessionId: string;
  campaignId?: string;
}

/**
 * Computes readiness metrics across session participants.
 * Non-spectator players are evaluated:
 * - Active players: isAbsent == false
 * - Ready players: isAbsent == false && isReady == true
 * - Stand-in players: isAbsent == true
 */
export function computeReadinessSummary(participants: LobbyParticipant[]): ReadinessSummary {
  // Exclude spectators and DM/owner coordinators from player count if players exist
  const players = participants.filter((p) => {
    const role = (p.role || '').toLowerCase();
    return role !== 'spectator' && role !== 'dm' && role !== 'dungeon_master' && role !== 'owner';
  });

  // Fallback: If only DMs or all roles are present without explicit 'player'
  const evaluated = players.length > 0 ? players : participants.filter((p) => (p.role || '').toLowerCase() !== 'spectator');

  const absentList = evaluated.filter((p) => p.isAbsent);
  const activeList = evaluated.filter((p) => !p.isAbsent);
  const readyList = activeList.filter((p) => p.isReady);

  const readyCount = readyList.length;
  const totalActivePlayers = activeList.length;
  const absentCount = absentList.length;
  const totalPlayers = evaluated.length;

  const allReady = totalActivePlayers > 0 && readyCount === totalActivePlayers;

  let summaryText = '';
  if (absentCount > 0) {
    const standInPlural = absentCount === 1 ? '1 absent stand-in' : `${absentCount} absent stand-ins`;
    summaryText = `${readyCount} of ${totalPlayers} players ready, ${standInPlural}`;
  } else {
    summaryText = `${readyCount} of ${totalPlayers} players ready`;
  }

  return {
    readyCount,
    totalActivePlayers,
    absentCount,
    allReady,
    summaryText,
  };
}
