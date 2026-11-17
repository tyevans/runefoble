/**
 * App Shell Session Data Loader (TASK-0640b).
 *
 * Loads the pre-game lobby and the live tabletop state for session routes.
 */

import type { MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { dataOk } from '../services/data-result.ts';
import { failLoad } from './load-error.ts';

/** Loads lobby participants, available characters, and the roster for a lobby route. */
export async function loadLobbyData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const cId = route.params.campaignId || host.campaignId;
  const sId = route.params.sessionId || host.sessionId;
  const [lobby, chars] = await Promise.all([
    appDataService.fetchLobbyState(cId, sId),
    host.characters.length > 0 ? Promise.resolve(dataOk(host.characters)) : appDataService.fetchCharacters(),
  ]);
  if (!lobby.ok || !chars.ok) return failLoad(host, lobby, chars);
  host.lobbyParticipants = lobby.data.participants;
  host.lobbyAvailableCharacters = lobby.data.availableCharacters;
  host.characters = chars.data;
}

/** Loads the board, session events, and roster for an active session route. */
export async function loadActiveSessionData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const cId = route.params.campaignId || host.campaignId;
  const sId = route.params.sessionId || host.sessionId;
  const [boardData, events, chars] = await Promise.all([
    appDataService.fetchBoardState(sId),
    appDataService.fetchSessionEvents(sId),
    host.characters.length > 0 ? Promise.resolve(dataOk(host.characters)) : appDataService.fetchCharacters(),
  ]);
  if (!boardData.ok || !events.ok || !chars.ok) return failLoad(host, boardData, events, chars);
  host.tokens = boardData.data.tokens.map((bt) => {
    const existing = host.tokens.find((t) => t.id === bt.id || (bt.id === 't1' && t.id === '1') || (bt.id === '1' && t.id === 't1'));
    return existing ? { ...bt, x: existing.x, y: existing.y } : bt;
  });
  host.boardCols = boardData.data.cols;
  host.boardRows = boardData.data.rows;
  host.atmosphere = { location_name: host.sessionTitle || 'Sanctum of Runes' };
  const liveEvents = host.events.filter((e) => !events.data.some((ev) => ev.id === e.id));
  host.events = [...events.data, ...liveEvents];
  host.characters = chars.data;
  host.resolveActiveCharacter(cId);
}
