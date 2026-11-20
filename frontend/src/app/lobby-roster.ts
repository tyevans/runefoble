/**
 * App Shell Lobby Roster Reads (TASK-0952, TASK-0974 follow-up).
 *
 * game_session owns the seats, the readiness and the stand-in state. The lobby reads the roster
 * when the route loads, when the session socket opens, after a saved change, and after each
 * readiness or stand-in frame. The read after the socket opens closes the gap between the first
 * read and the subscription. Only the newest read changes the page, so an older answer that
 * arrives late never replaces a newer one.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';

type RosterHost = Pick<RunefobleApp, 'campaignId' | 'sessionId' | 'lobbyParticipants' | 'lobbyAvailableCharacters' | 'showToast'>;

let latestRead = 0;

/** True when the route is the session lobby. */
export function isLobbyRoute(pattern: string | undefined): boolean {
  return Boolean(pattern?.includes('/lobby/'));
}

/** Reads the roster again from the owner. The stored readiness and presence replace the page state. */
export async function reloadLobbyRoster(host: RosterHost, sessionId: string): Promise<void> {
  latestRead += 1;
  const readNo = latestRead;
  const lobby = await appDataService.fetchLobbyState(host.campaignId, sessionId);
  if (readNo !== latestRead || host.sessionId !== sessionId) return;
  if (!lobby.ok) {
    host.showToast(`The roster did not load: ${lobby.message}`);
    return;
  }
  host.lobbyParticipants = lobby.data.participants;
  host.lobbyAvailableCharacters = lobby.data.availableCharacters;
}
