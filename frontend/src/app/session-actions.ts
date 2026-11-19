/**
 * App Shell Session Actions (TASK-0643).
 *
 * Handles the lobby events that seat a player, start a live session, and activate an absentee
 * stand-in. Each lobby change that the owner records goes through an HTTP route.
 */

import type { TakeSeatEventDetail } from '@runefoble/game-session-ui';
import { appDataService } from '../services/app-data-service.ts';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleToggleStandIn } from '../vtt-mesh-handlers.ts';

/**
 * Starts the session through the gateway start route, then opens the live tabletop (TASK-0910).
 * game_session moves the session from `lobby` to `active` and checks `session.control`. The
 * gateway then sends `session_started` to the other sockets. A refusal shows the owner's message
 * and keeps the lobby. The shell sends no socket frame.
 */
export async function launchSession(host: RunefobleApp, e: CustomEvent): Promise<void> {
  const cId = e.detail?.campaignId || host.campaignId;
  const sId = e.detail?.sessionId || host.sessionId;
  if (!cId || !sId) {
    host.showToast('Session not launched. The campaign or session is not known.');
    return;
  }
  const started = await appDataService.startSession(sId);
  if (!started.ok) {
    host.showToast(`Session not launched: ${started.message}`);
    return;
  }
  await router.navigate(`#/campaigns/${cId}/sessions/${sId}`);
}

/** Toggles the stand-in for a player. An absent player opens the directives drawer. */
export function toggleStandIn(host: RunefobleApp, e: CustomEvent): void {
  handleToggleStandIn(host, e, host.sessionSocket.current);
  if (e.detail?.isAbsent) {
    host.isAbsenteeDirectiveOpen = true;
    host.showToast('Stand-In Activated: Directives drawer opened');
  }
}

/**
 * Seats the caller through the gateway join route, then reads the lobby roster again (TASK-0889).
 * game_session checks `session.participate`. A refusal shows the owner's message and keeps the roster.
 */
export async function takeLobbySeat(host: RunefobleApp, e: CustomEvent<TakeSeatEventDetail>): Promise<void> {
  const sId = e.detail?.sessionId || host.sessionId;
  const seat = e.detail;
  if (!sId || !seat?.characterId) {
    host.showToast('Seat not taken. The session or the character is not known.');
    return;
  }
  const joined = await appDataService.joinSession(sId, {
    character_id: seat.characterId, character_name: seat.characterName, character_class: seat.characterClass,
  });
  if (!joined.ok) {
    host.showToast(`Seat not taken: ${joined.message}`);
    return;
  }
  const lobby = await appDataService.fetchLobbyState(host.campaignId, sId);
  if (!lobby.ok) {
    host.showToast(`Seat taken, but the roster did not load: ${lobby.message}`);
    return;
  }
  host.lobbyParticipants = lobby.data.participants;
  host.lobbyAvailableCharacters = lobby.data.availableCharacters;
}
