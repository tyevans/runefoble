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

/** The number of the newest board read that started for each host (TASK-0938). */
const newestBoardRead = new WeakMap<RunefobleApp, number>();

/** Numbers a new board read. Each read is numbered in the order that it starts. */
function startBoardRead(host: RunefobleApp): number {
  const readNo = (newestBoardRead.get(host) ?? 0) + 1;
  newestBoardRead.set(host, readNo);
  return readNo;
}

/**
 * Copies the session board to the host. A session without a board keeps no tokens, and the
 * view shows the no-battlemap state in the board area (TASK-0906).
 * A read that answers after a newer read started is dropped (TASK-0938). Its tokens are older
 * than the newer read, and they would move the board back.
 */
function applyBoard(host: RunefobleApp, board: SessionBoard, readNo: number): void {
  if (newestBoardRead.get(host) !== readNo) return;
  host.boardKind = board.kind;
  if (board.kind === 'no_board') {
    host.tokens = [];
    return;
  }
  // The read is the server state. A cell shown before the read can be older than it.
  host.tokens = board.tokens;
  host.boardCols = board.cols;
  host.boardRows = board.rows;
}

/**
 * Copies the owner's session status to the host. `ended` is final: a read that started before the
 * end and answers after it cannot move the status back to `active` (TASK-0953).
 */
export function applySessionStatus(host: RunefobleApp, status: string): void {
  host.sessionStatus = host.sessionStatus === 'ended' || status === 'ended' ? 'ended' : status;
}

/**
 * Loads the board, session events, and roster for an active session route.
 * A missing board is not a load failure. Any other failed read replaces the view with the error state.
 */
export async function loadActiveSessionData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  const cId = route.params.campaignId ?? '';
  const sId = route.params.sessionId ?? '';
  const readNo = startBoardRead(host);
  const [boardData, events, chars, camp, caps, status] = await Promise.all([
    appDataService.fetchBoardState(sId),
    appDataService.fetchSessionEvents(sId),
    host.characters.length > 0 ? Promise.resolve(dataOk(host.characters)) : appDataService.fetchCharacters(),
    appDataService.fetchCampaign(cId),
    appDataService.fetchCampaignCapabilities(cId),
    appDataService.fetchSessionStatus(sId),
  ]);
  if (!boardData.ok || !events.ok || !chars.ok || !camp.ok || !caps.ok || !status.ok) {
    return failLoad(host, boardData, events, chars, camp, caps, status);
  }
  // The DM sets up a missing board with one token for each seat, so the DM view needs the seats (TASK-0922).
  const needsSeats = boardData.data.kind === 'no_board' && caps.data.run_session === true;
  const seats = needsSeats ? await appDataService.fetchSessionSeats(sId) : dataOk([]);
  if (!seats.ok) return failLoad(host, seats);
  setCurrentCampaign(host, camp.data);
  setCampaignCapabilities(host, caps.data);
  applyBoard(host, boardData.data, readNo);
  applySessionStatus(host, status.data);
  host.sessionSeats = seats.data;
  host.atmosphere = { location_name: host.sessionTitle };
  const liveEvents = host.events.filter((e) => !events.data.some((ev) => ev.id === e.id));
  host.events = [...events.data, ...liveEvents];
  host.characters = chars.data;
  host.resolveActiveCharacter(cId);
}
