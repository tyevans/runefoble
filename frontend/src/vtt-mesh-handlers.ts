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
 * ADR-0004, ADR-0005, ADR-0010, ADR-0013.
 */

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

export function handleToggleReadiness(host: any, e: CustomEvent, socket: WebSocket | null): void {
  const { userId, isReady } = e.detail || {};
  if (!userId) return;
  host.lobbyParticipants = host.lobbyParticipants.map((p: any) => (p.userId === userId ? { ...p, isReady } : p));
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'player_readiness', userId, isReady }));
  }
}

export function handleToggleStandIn(host: any, e: CustomEvent, socket: WebSocket | null): void {
  const { userId, isAbsent } = e.detail || {};
  if (!userId) return;
  host.lobbyParticipants = host.lobbyParticipants.map((p: any) => (p.userId === userId ? { ...p, isAbsent } : p));
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'player_stand_in', userId, isAbsent }));
  }
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
