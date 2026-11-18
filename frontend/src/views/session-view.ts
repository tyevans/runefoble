/**
 * Active Session View (TASK-0643). Renders the live tabletop or the spectator view.
 */

import { html } from 'lit';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleBoardAoEPlace, handleBoardConfirmGhost, handleBoardSpellVFX, handleBoardTokenAction } from '../vtt-mesh-handlers.ts';
import { switchDmCharacter } from '../app/character-actions.ts';

/** Renders the live tabletop (party mode) or the spectator view for an active session. */
export function renderSessionActive(app: RunefobleApp) {
  const char = app.activeCharacter ?? app.resolveActiveCharacter(app.campaignId);
  const isOwnerOrDm = app.isDM || app.currentCampaign?.role === 'owner' || app.currentCampaign?.role === 'dm';
  if (app.viewMode === 'spectator') {
    return html`<runefoble-spectator-view .sessionId=${app.sessionId} .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${app.tokens} .atmosphere=${app.atmosphere} .chronicle=${app.events}></runefoble-spectator-view>`;
  }
  return html`<div class="layout-grid">
    <div class="board-column">
      <runefoble-plugin-slot slot-id="hud-widget" .showFallback=${false}></runefoble-plugin-slot>
      <runefoble-board .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${app.tokens} .fogOfWar=${true} .websocketUrl=${app.getWebSocketUrl()} @token-action=${(e: CustomEvent) => handleBoardTokenAction(e, app.sessionSocket.current)} @aoe-place=${(e: CustomEvent) => handleBoardAoEPlace(e, app.sessionSocket.current)} @spell-vfx-triggered=${(e: CustomEvent) => handleBoardSpellVFX(e, app.sessionSocket.current)} @confirm-ghost=${(e: CustomEvent) => handleBoardConfirmGhost(e, app.sessionSocket.current)}></runefoble-board>
    </div>
    <div class="character-column">
      ${isOwnerOrDm ? html`<div class="dm-party-inspector" role="region" aria-label="DM Party Inspector"><span class="dm-badge">DM Party Inspector</span><select class="dm-character-switcher" aria-label="Switch inspected character" @change=${(e: Event) => switchDmCharacter(app, (e.target as HTMLSelectElement).value)}>${app.characters.map((c) => html`<option value="${c.id}" ?selected=${c.id === char?.id}>${c.name} (${c.characterClass} Lv ${c.level})</option>`)}</select></div>` : ''}
      ${char ? html`<runefoble-character-card .characterName=${char.name} .characterClass=${`${char.characterClass}${char.level ? ` Lvl ${char.level}` : ''}`} .level=${char.level} .currentHp=${char.currentHp} .maxHp=${char.maxHp} .armorClass=${char.armorClass} .portraitUrl=${char.portraitUrl || ''} .isAiStandIn=${Boolean(char.isAiStandIn)}></runefoble-character-card>
      <button class="btn-toggle-directive" @click=${() => { app.isAbsenteeDirectiveOpen = true; }}>📋 Stance Directives</button>` : html`<div class="empty-state" data-testid="active-character-empty"><p>No character is bound to this session. Choose a character in the session lobby.</p></div>`}
      <runefoble-plugin-slot slot-id="sidebar-tool" .showFallback=${false}></runefoble-plugin-slot>
      <runefoble-plugin-slot slot-id="dice-panel" .showFallback=${false}></runefoble-plugin-slot>
    </div>
    <runefoble-watcher-feed .events=${app.events}></runefoble-watcher-feed>
  </div>
  <div class="voice-container">
    <runefoble-voice-controls .isListening=${app.isListening} @voice-toggle=${() => { app.isListening = !app.isListening; }}></runefoble-voice-controls>
  </div>`;
}
