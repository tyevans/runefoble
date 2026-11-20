/**
 * App Shell Session Message Handler (TASK-0640b).
 *
 * Applies live session WebSocket messages to App Shell state. The session socket does the
 * session_started route change, because it drives routing. `sessionStartedRoute` decides it.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { toWatcherFeedEvent, type SessionChronicleEntry } from '../services/session-chronicle.ts';
import { dispatchSessionMessage } from '../vtt-mesh-handlers.ts';
import { handleBoardReady } from './board-setup-actions.ts';
import { isLobbyRoute, reloadLobbyRoster } from './lobby-roster.ts';

function clockTime(): string {
  return new Date().toLocaleTimeString();
}

/** The shell ids that a `session_started` message must match. */
export interface ShellSessionIds {
  campaignId: string;
  sessionId: string;
}

/**
 * Returns the live tabletop route for a `session_started` message, or null (TASK-0910).
 * The message must name the shell's own session and carry `status: 'active'`. The route uses
 * the shell's own ids, never ids from the message.
 */
export function sessionStartedRoute(shell: ShellSessionIds, msg: { sessionId?: unknown; status?: unknown }): string | null {
  if (!shell.campaignId || !shell.sessionId) return null;
  if (msg.sessionId !== shell.sessionId || msg.status !== 'active') return null;
  return `#/campaigns/${shell.campaignId}/sessions/${shell.sessionId}`;
}

/** The host fields that the end of a session changes. */
export type SessionEndHost = Pick<RunefobleApp, 'sessionId' | 'sessionStatus' | 'isEndSessionConfirmOpen' | 'reloadRouteData'>;

/**
 * Moves the App Shell to the recap of an ended session (TASK-0953). The view shows the recap when
 * the status is `ended`. A reload then reads the committed chronicle, so every line of the recap
 * comes from the server, in commit order.
 */
export function markSessionEnded(host: SessionEndHost): void {
  host.sessionStatus = 'ended';
  host.isEndSessionConfirmOpen = false;
  host.reloadRouteData();
}

/**
 * Applies a `session_ended` frame to the shell (TASK-0953). The frame must name the shell's own
 * session and carry `status: 'ended'`. Any other frame changes nothing.
 */
export function applySessionEndedFrame(host: SessionEndHost, msg: { sessionId?: unknown; status?: unknown }): boolean {
  if (msg.sessionId !== host.sessionId || msg.status !== 'ended') return false;
  markSessionEnded(host);
  return true;
}

/** Adds a live chronicle line to the feed. A line that the feed already holds is not added again. */
function appendChronicleEntry(host: RunefobleApp, entry: SessionChronicleEntry): void {
  if (host.events.some((e) => e.id === entry.event_id)) return;
  host.events = [...host.events, toWatcherFeedEvent(entry)];
}

/** Each live roll gets a local row key. The `dice_rolled` frame has no event id. */
let diceRowSeq = 0;

/** Adds the live line of one `dice_rolled` frame: the roller's name, the formula and the total. */
function appendDiceRoll(host: RunefobleApp, msg: { rollerName?: unknown; formula?: unknown; total?: unknown }): void {
  diceRowSeq += 1;
  appendChronicleEntry(host, {
    event_id: `dice-roll-${diceRowSeq}`,
    kind: 'dice_roll',
    occurred_at: new Date().toISOString(),
    speaker: String(msg.rollerName ?? ''),
    text: `${String(msg.formula ?? '')} = ${String(msg.total ?? '')}`,
    penalties: [],
  });
}

/**
 * A seat frame on the lobby route reads the roster again. The frame patch shows the change at
 * once. The read adds a seat that the page did not have yet when the frame came.
 */
function rereadLobbyRoster(host: RunefobleApp): void {
  if (isLobbyRoute(host.currentRoute?.pattern) && host.sessionId) void reloadLobbyRoster(host, host.sessionId);
}

/** Routes one parsed session message to the matching state update or VTT handler. */
export function handleSessionMessage(host: RunefobleApp, msg: any): void {
  if (msg.type === 'speech_action') {
    host.events = [
      ...host.events,
      { id: String(Date.now()), timestamp: clockTime(), source: 'player', speaker: msg.speaker || 'Party Member', text: msg.transcript || '', actionType: 'speech' },
    ];
  } else if (msg.type === 'chronicle_entry') {
    appendChronicleEntry(host, msg.entry);
  } else if (msg.type === 'dice_rolled') {
    appendDiceRoll(host, msg);
    dispatchSessionMessage(msg);
  } else if (msg.type === 'player_readiness') {
    host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === msg.userId ? { ...p, isReady: msg.isReady } : p));
    rereadLobbyRoster(host);
  } else if (msg.type === 'player_stand_in') {
    host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === msg.userId ? { ...p, isAbsent: msg.isAbsent } : p));
    host.sessionParticipants = host.sessionParticipants.map((p) => (p.userId === msg.userId ? { ...p, isStandInActive: msg.isAbsent === true } : p));
    rereadLobbyRoster(host);
  } else if (msg.type === 'board_ready') {
    handleBoardReady(host, msg);
  } else {
    dispatchSessionMessage(msg);
  }
}
