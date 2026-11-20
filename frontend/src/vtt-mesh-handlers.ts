/**
 * Live Tabletop VTT WebSocket Mesh & Tangential Action Handlers.
 *
 * Dispatches VTT board actions (radial menu, AoE templates, spell VFX, ghost confirmations)
 * to the session socket. Forwards incoming session messages for dice rolls, turn changes,
 * AoEs, spell VFX, and DM whispers as window events. The microfrontends that own those
 * features subscribe to the events. The shell never queries service element tags.
 * Event contract: docs/reference/microfrontend-architecture.md, "Session Mesh Events".
 * TASK-0358: Live Tabletop VTT WebSocket Event Mesh & Plugin Slots Integration.
 * TASK-0826: App Shell stops reaching into service component internals (audit F-07).
 * Lobby readiness and stand-in changes do not use this socket. They go through owner routes
 * (session-actions.ts, TASK-0952).
 * TASK-0945: the typed command bar posts its command to the gateway speak-and-act route.
 * ADR-0004, ADR-0005, ADR-0010, ADR-0013, ADR-0022 (c).
 */

import type { CommandBarStatus, SpeakCommandBody } from '@runefoble/the-watcher-ui';
import { requestData } from './services/shell-request.ts';

export const SPEAK_AND_ACT_PATH = '/api/v1/watcher/speak-and-act';

/** Session message types that the shell forwards, mapped to the window event they dispatch. */
const SESSION_MESH_EVENTS: Readonly<Record<string, string>> = {
  dice_rolled: 'runefoble:dice-rolled',
  turn_advanced: 'runefoble:turn-advanced',
  aoe_placed: 'runefoble:aoe-placed',
  spell_vfx: 'runefoble:spell-vfx',
  dm_whisper: 'runefoble:dm-whisper',
};

/**
 * Dispatches one incoming session message as a window event. The event detail is the message.
 * Returns false when the message type has no microfrontend event.
 */
export function dispatchSessionMessage(msg: { type?: unknown }): boolean {
  const type = typeof msg.type === 'string' && Object.hasOwn(SESSION_MESH_EVENTS, msg.type) ? msg.type : null;
  if (!type) return false;
  globalThis.dispatchEvent(new CustomEvent(SESSION_MESH_EVENTS[type], { detail: msg }));
  return true;
}

export function handleBoardTokenAction(e: CustomEvent, socket: WebSocket | null): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'token_action', ...e.detail }));
  }
}

export function handleBoardAoEPlace(e: CustomEvent, socket: WebSocket | null): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'aoe_placed', ...e.detail }));
  }
}

export function handleBoardSpellVFX(e: CustomEvent, socket: WebSocket | null): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'spell_vfx', ...e.detail }));
  }
}

export function handleBoardConfirmGhost(e: CustomEvent, socket: WebSocket | null): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'confirm_ghost', ...e.detail }));
  }
}

/** The host state that the typed command handler sets. */
export interface SpeakCommandHost {
  commandStatus: CommandBarStatus;
}

/** The status of a 2xx reply: the Watcher reply, or an error when the reply has none. */
function replyStatus(data: { watcher_reply?: unknown }): CommandBarStatus {
  const reply = data.watcher_reply;
  if (typeof reply === 'string' && reply.trim()) return { kind: 'reply', text: reply };
  return { kind: 'error', text: 'The Watcher sent a reply without watcher_reply.' };
}

/**
 * Posts one typed command to The Watcher through the gateway, with the shell bearer. A move
 * reply stages the ghost preview on the board socket, so this handler stages nothing. A refused
 * or failed call shows its status and detail in the bar (ADR-0022 c). Nothing is retried.
 */
export async function handleSpeakCommand(host: SpeakCommandHost, e: CustomEvent<SpeakCommandBody>): Promise<void> {
  host.commandStatus = { kind: 'sending' };
  const res = await requestData<{ watcher_reply?: unknown }>(SPEAK_AND_ACT_PATH, { method: 'POST', body: JSON.stringify(e.detail) });
  if (res.ok) {
    host.commandStatus = replyStatus(res.data);
    return;
  }
  host.commandStatus = { kind: 'error', text: res.status === 0 ? res.message : `HTTP ${res.status}: ${res.message}` };
}
