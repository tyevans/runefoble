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

/** Adds a live chronicle line to the feed. A line that the feed already holds is not added again. */
function appendChronicleEntry(host: RunefobleApp, entry: SessionChronicleEntry): void {
  if (host.events.some((e) => e.id === entry.event_id)) return;
  host.events = [...host.events, toWatcherFeedEvent(entry)];
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
  } else if (msg.type === 'player_readiness') {
    host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === msg.userId ? { ...p, isReady: msg.isReady } : p));
  } else if (msg.type === 'player_stand_in') {
    host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === msg.userId ? { ...p, isAbsent: msg.isAbsent } : p));
  } else if (msg.type === 'board_ready') {
    handleBoardReady(host, msg);
  } else {
    dispatchSessionMessage(msg);
  }
}
