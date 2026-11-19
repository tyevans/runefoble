/**
 * App Shell Session Data Loader (TASK-0640b).
 *
 * Loads the pre-game lobby and the live tabletop state for session routes.
 */

import type { MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { dataOk } from '../services/data-result.ts';
import type { SessionBoard } from '../services/session-board.ts';
import { failLoad } from './load-error.ts';
import { setCampaignCapabilities, setCurrentCampaign } from './shell-state.ts';

/** Loads lobby participants, available characters, and the roster for a lobby route. */
export async function loadLobbyData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const cId = route.params.campaignId ?? '';
  const sId = route.params.sessionId ?? '';
  const [lobby, chars, camp, caps] = await Promise.all([
    appDataService.fetchLobbyState(cId, sId),
    host.characters.length > 0 ? Promise.resolve(dataOk(host.characters)) : appDataService.fetchCharacters(),
    appDataService.fetchCampaign(cId),
    appDataService.fetchCampaignCapabilities(cId),
  ]);
  if (!lobby.ok || !chars.ok || !camp.ok || !caps.ok) return failLoad(host, lobby, chars, camp, caps);
  setCurrentCampaign(host, camp.data);
  setCampaignCapabilities(host, caps.data);
  host.lobbyParticipants = lobby.data.participants;
  host.lobbyAvailableCharacters = lobby.data.availableCharacters;
  host.characters = chars.data;
}

/**
 * Copies the session board to the host. A session without a board keeps no tokens, and the
 * view shows the no-battlemap state in the board area (TASK-0906).
 */
function applyBoard(host: RunefobleApp, board: SessionBoard): void {
  host.boardKind = board.kind;
  if (board.kind === 'no_board') {
    host.tokens = [];
    return;
  }
  host.tokens = board.tokens.map((bt) => {
    const existing = host.tokens.find((t) => t.id === bt.id);
    return existing ? { ...bt, x: existing.x, y: existing.y } : bt;
  });
  host.boardCols = board.cols;
  host.boardRows = board.rows;
}

/**
 * Loads the board, session events, and roster for an active session route.
 * A missing board is not a load failure. Any other failed read replaces the view with the error state.
 */
export async function loadActiveSessionData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const cId = route.params.campaignId ?? '';
  const sId = route.params.sessionId ?? '';
  const [boardData, events, chars, camp, caps] = await Promise.all([
    appDataService.fetchBoardState(sId),
    appDataService.fetchSessionEvents(sId),
    host.characters.length > 0 ? Promise.resolve(dataOk(host.characters)) : appDataService.fetchCharacters(),
    appDataService.fetchCampaign(cId),
    appDataService.fetchCampaignCapabilities(cId),
  ]);
  if (!boardData.ok || !events.ok || !chars.ok || !camp.ok || !caps.ok) return failLoad(host, boardData, events, chars, camp, caps);
  setCurrentCampaign(host, camp.data);
  setCampaignCapabilities(host, caps.data);
  applyBoard(host, boardData.data);
  host.atmosphere = { location_name: host.sessionTitle };
  const liveEvents = host.events.filter((e) => !events.data.some((ev) => ev.id === e.id));
  host.events = [...events.data, ...liveEvents];
  host.characters = chars.data;
  host.resolveActiveCharacter(cId);
}
