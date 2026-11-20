/**
 * App Shell Session Actions (TASK-0643).
 *
 * Handles the lobby events that seat a player, start a live session, and activate an absentee
 * stand-in. Each lobby change that the owner records goes through an HTTP route.
 */

import type { TakeSeatEventDetail, ToggleReadinessEventDetail, ToggleStandInEventDetail } from '@runefoble/game-session-ui';
import { appDataService } from '../services/app-data-service.ts';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { markSessionEnded } from './session-messages.ts';

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

/**
 * Ends the active session through the gateway end route (TASK-0953). game_session checks
 * `session.control`. A refusal shows the owner's message and keeps the session live. A success
 * shows the recap; the `session_ended` frame gives the same result to every other view.
 */
export async function endSession(host: RunefobleApp): Promise<void> {
  const sId = host.sessionId;
  if (!sId) {
    host.showToast('Session not ended. The session is not known.');
    return;
  }
  const ended = await appDataService.endSession(sId);
  if (!ended.ok) {
    host.isEndSessionConfirmOpen = false;
    host.showToast(`Session not ended: ${ended.message}`);
    return;
  }
  markSessionEnded(host);
}

/**
 * Forces the lobby to render again, so each checkbox shows the roster state. A failed write
 * leaves the roster as it was, and the checkbox must go back to that state (TASK-0952).
 */
function rerenderRoster(host: RunefobleApp): void {
  host.lobbyParticipants = [...host.lobbyParticipants];
}

/** Reads the roster again from the owner. The stored readiness and presence replace the page state. */
async function reloadRoster(host: RunefobleApp, sId: string): Promise<void> {
  const lobby = await appDataService.fetchLobbyState(host.campaignId, sId);
  if (!lobby.ok) {
    host.showToast(`The roster did not load: ${lobby.message}`);
    return;
  }
  host.lobbyParticipants = lobby.data.participants;
  host.lobbyAvailableCharacters = lobby.data.availableCharacters;
}

/**
 * Saves the caller's readiness through the gateway route (TASK-0952). The owner stores it, and
 * the roster is read again. A refusal shows the owner's message and restores the checkbox.
 */
export async function toggleReadiness(host: RunefobleApp, e: CustomEvent<ToggleReadinessEventDetail>): Promise<void> {
  const sId = e.detail?.sessionId || host.sessionId;
  if (!sId) {
    host.showToast('Readiness not saved. The session is not known.');
    rerenderRoster(host);
    return;
  }
  const saved = await appDataService.setLobbyReadiness(sId, e.detail.isReady === true);
  if (!saved.ok) {
    host.showToast(`Readiness not saved: ${saved.message}`);
    rerenderRoster(host);
    return;
  }
  await reloadRoster(host, sId);
}

/**
 * Sets or releases the AI stand-in of a seat (TASK-0952). A player sets their own seat. The DM sets
 * any seat. game_session activates the lobby character's stand-in, or releases it. The roster is
 * read again after a saved change. An absent seat opens the directives drawer when the player set it.
 */
export async function toggleStandIn(host: RunefobleApp, e: CustomEvent<ToggleStandInEventDetail>): Promise<void> {
  const sId = e.detail?.sessionId || host.sessionId;
  const userId = e.detail?.userId;
  const isAbsent = e.detail?.isAbsent === true;
  if (!sId || !userId) {
    host.showToast('Stand-in not changed. The session or the player is not known.');
    rerenderRoster(host);
    return;
  }
  const saved = await appDataService.setSeatStandIn(sId, userId, isAbsent);
  if (!saved.ok) {
    host.showToast(`Stand-in not changed: ${saved.message}`);
    rerenderRoster(host);
    return;
  }
  await reloadRoster(host, sId);
  if (isAbsent && userId === host.currentUserId) {
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
  // The owner stands in with the lobby character, so the seat records it (TASK-0952).
  const picked = await appDataService.selectLobbyCharacter(sId, seat.characterId);
  if (!picked.ok) host.showToast(`Seat taken, but the lobby character was not saved: ${picked.message}`);
  const lobby = await appDataService.fetchLobbyState(host.campaignId, sId);
  if (!lobby.ok) {
    host.showToast(`Seat taken, but the roster did not load: ${lobby.message}`);
    return;
  }
  host.lobbyParticipants = lobby.data.participants;
  host.lobbyAvailableCharacters = lobby.data.availableCharacters;
}
