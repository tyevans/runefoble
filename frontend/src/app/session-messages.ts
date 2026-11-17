/**
 * App Shell Session Message Handler (TASK-0640b).
 *
 * Applies live session WebSocket messages to App Shell state. The session_started
 * route change stays in runefoble-app.ts because it drives routing.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import {
  handleIncomingAoEPlaced,
  handleIncomingDiceRoll,
  handleIncomingDmWhisper,
  handleIncomingSpellVFX,
  handleIncomingTurnAdvanced,
} from '../vtt-mesh-handlers.ts';

function clockTime(): string {
  return new Date().toLocaleTimeString();
}

/** Routes one parsed session message to the matching state update or VTT handler. */
export function handleSessionMessage(host: RunefobleApp, msg: any): void {
  if (msg.type === 'speech_action') {
    host.events = [
      ...host.events,
      { id: String(Date.now()), timestamp: clockTime(), source: 'player', speaker: msg.speaker || 'Party Member', text: msg.transcript || '', actionType: 'speech' },
    ];
  } else if (msg.type === 'player_readiness') {
    host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === msg.userId ? { ...p, isReady: msg.isReady } : p));
  } else if (msg.type === 'player_stand_in') {
    host.lobbyParticipants = host.lobbyParticipants.map((p) => (p.userId === msg.userId ? { ...p, isAbsent: msg.isAbsent } : p));
  } else if (msg.type === 'dice_rolled') handleIncomingDiceRoll(host, msg);
  else if (msg.type === 'turn_advanced') handleIncomingTurnAdvanced(host, msg);
  else if (msg.type === 'aoe_placed') handleIncomingAoEPlaced(host, msg);
  else if (msg.type === 'spell_vfx') handleIncomingSpellVFX(host, msg);
  else if (msg.type === 'dm_whisper') handleIncomingDmWhisper(host, msg);
}
