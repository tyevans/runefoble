/**
 * Live Tabletop VTT WebSocket Mesh & Tangential Action Handlers.
 *
 * Dispatches VTT board actions (radial menu, AoE templates, spell VFX, ghost confirmations)
 * and handles incoming WebSocket messages for dice rolls, turn changes, AoEs, and DM whispers.
 * TASK-0358: Live Tabletop VTT WebSocket Event Mesh & Plugin Slots Integration.
 * ADR-0004, ADR-0005, ADR-0010, ADR-0013.
 */

import type { LitElement } from 'lit';

export function getMountedPluginElement<T extends HTMLElement = HTMLElement>(host: LitElement, tag: string): T | null {
  const direct = host.shadowRoot?.querySelector(tag);
  if (direct) return direct as T;
  const slots = host.shadowRoot?.querySelectorAll('runefoble-plugin-slot') || [];
  for (const slot of slots) {
    const el = slot.shadowRoot?.querySelector(tag);
    if (el) return el as T;
  }
  return null;
}

export function handleIncomingDiceRoll(host: any, msg: any): void {
  const diceTray = getMountedPluginElement<any>(host, 'runefoble-dice-tray-3d');
  if (diceTray && typeof diceTray.roll === 'function') {
    diceTray.roll(msg.diceType || 'd20', msg.targetFaceValue ?? msg.total ?? msg.result, msg.opts);
  }
  const diceRoller = getMountedPluginElement<any>(host, 'runefoble-dice-roller');
  if (diceRoller && msg.result) diceRoller.forcedResult = msg.result;
  const board = host.shadowRoot?.querySelector('runefoble-board') as any;
  if (board && typeof board.roll3DDice === 'function') {
    board.roll3DDice(msg.dice || { diceType: msg.diceType || 'd20', face: msg.targetFaceValue ?? msg.total });
  }
}

export function handleIncomingTurnAdvanced(host: any, msg: any): void {
  const tracker = getMountedPluginElement<any>(host, 'runefoble-initiative-tracker');
  if (tracker) {
    if (msg.activeCombatantId) tracker.activeCombatantId = msg.activeCombatantId;
    if (msg.roundNumber) tracker.roundNumber = msg.roundNumber;
    else if (typeof tracker.nextTurn === 'function') tracker.nextTurn();
  }
  const board = host.shadowRoot?.querySelector('runefoble-board') as any;
  if (board && msg.activeCombatantId) board.activeTurnTokenId = msg.activeCombatantId;
}

export function handleIncomingAoEPlaced(host: any, msg: any): void {
  const board = host.shadowRoot?.querySelector('runefoble-board') as any;
  if (board) {
    board.activeAoE = msg.template || msg.config || msg.aoe || null;
    if (typeof board.handleIncomingSocketMessage === 'function') {
      board.handleIncomingSocketMessage({ action: 'aoe_placed', ...msg });
    }
  }
}

export function handleIncomingSpellVFX(host: any, msg: any): void {
  const board = host.shadowRoot?.querySelector('runefoble-board') as any;
  if (board && typeof board.triggerSpellVFX === 'function') {
    board.triggerSpellVFX(msg.vfx || msg.params || msg);
  }
}

export function handleIncomingDmWhisper(host: any, msg: any): void {
  const whisperBar = getMountedPluginElement<any>(host, 'runefoble-dm-whisper-bar');
  if (whisperBar) {
    const whisper = msg.whisper || {
      whisper_id: msg.whisper_id || `whisp-${Date.now()}`,
      whisper_type: msg.whisper_type || 'atmospheric_hint',
      content: msg.content || msg.text || '',
      timestamp: msg.timestamp || new Date().toLocaleTimeString(),
    };
    whisperBar.whispers = [...(whisperBar.whispers || []), whisper];
    if (msg.pendingAction) whisperBar.pendingAction = msg.pendingAction;
  }
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
