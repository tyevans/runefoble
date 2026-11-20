/**
 * Active Session View (TASK-0643). Renders the live tabletop or the spectator view.
 */

import { html } from 'lit';
import { guard } from 'lit/directives/guard.js';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleBoardAoEPlace, handleBoardConfirmGhost, handleBoardSpellVFX, handleBoardTokenAction } from '../vtt-mesh-handlers.ts';
import { switchDmCharacter } from '../app/character-actions.ts';
import { recordBoardMoveTarget, resolveBoardDmAccess } from '../app/board-dm-controls.ts';
import { handleBoardSetUp } from '../app/board-setup-actions.ts';

/**
 * The DM trap controls and the map switcher for the board. The session id is the board id.
 * Only a caller with the `run_session` capability sees them. A map switch reloads the board from the server.
 */
function renderBoardDmControls(app: RunefobleApp) {
  if (resolveBoardDmAccess(app.campaignCapabilities) !== 'allowed') return '';
  return html`<div class="dm-board-controls" role="region" aria-label="DM Board Controls">
    <runefoble-dm-trap-controls .boardId=${app.sessionId} .targetX=${app.boardTarget?.targetX ?? null} .targetY=${app.boardTarget?.targetY ?? null} @open-map-switcher=${() => { app.isMapSwitcherOpen = true; }}></runefoble-dm-trap-controls>
    <runefoble-map-switcher .boardId=${app.sessionId} .open=${app.isMapSwitcherOpen} @switcher-closed=${() => { app.isMapSwitcherOpen = false; }} @map-switched=${() => { app.isMapSwitcherOpen = false; app.reloadRouteData(); }}></runefoble-map-switcher>
  </div>`;
}

/**
 * The board, or the no-battlemap state while the session has no board (TASK-0906).
 * The DM sets up the board from the no-battlemap state (TASK-0922).
 * The DM board controls act on a board, so they show only when the board exists.
 * Until the first board read answers, no `<runefoble-board>` mounts, so no board socket opens
 * before the board exists.
 * The board applies socket frames to its own `tokens`. Lit commits an array binding on every
 * render, so `guard` passes `app.tokens` only when a new board read replaces it. Without it, any
 * shell render (a chronicle frame, for example) puts the read tokens back over a move (TASK-0938).
 */
function renderBoardArea(app: RunefobleApp, canRunSession: boolean) {
  if (app.boardKind === 'loading') return html`<div class="board-loading" role="status" aria-live="polite">Loading the battlemap...</div>`;
  if (app.boardKind === 'no_board') return html`<runefoble-board-empty ?can-set-up-map=${canRunSession} .campaignId=${app.campaignId} .sessionId=${app.sessionId} .seats=${app.sessionSeats} @board-set-up=${(e: CustomEvent) => handleBoardSetUp(app, e)}></runefoble-board-empty>`;
  return html`<runefoble-board .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${guard([app.tokens], () => app.tokens)} .fogOfWar=${true} .websocketUrl=${app.getWebSocketUrl()} @token-action=${(e: CustomEvent) => handleBoardTokenAction(e, app.sessionSocket.current)} @aoe-place=${(e: CustomEvent) => handleBoardAoEPlace(e, app.sessionSocket.current)} @spell-vfx-triggered=${(e: CustomEvent) => handleBoardSpellVFX(e, app.sessionSocket.current)} @confirm-ghost=${(e: CustomEvent) => handleBoardConfirmGhost(e, app.sessionSocket.current)} @move-token=${(e: CustomEvent) => recordBoardMoveTarget(app, e)}></runefoble-board>
      ${renderBoardDmControls(app)}`;
}

/** Renders the live tabletop (party mode) or the spectator view for an active session. */
export function renderSessionActive(app: RunefobleApp) {
  const char = app.activeCharacter ?? app.resolveActiveCharacter(app.campaignId);
  const canRunSession = Boolean(app.campaignCapabilities?.run_session);
  if (app.viewMode === 'spectator') {
    return html`<runefoble-spectator-view .sessionId=${app.sessionId} .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${app.tokens} .atmosphere=${app.atmosphere} .chronicle=${app.events}></runefoble-spectator-view>`;
  }
  return html`<div class="layout-grid">
    <div class="board-column">
      <runefoble-plugin-slot slot-id="hud-widget" .showFallback=${false}></runefoble-plugin-slot>
      ${renderBoardArea(app, canRunSession)}
    </div>
    <div class="character-column">
      ${canRunSession ? html`<div class="dm-party-inspector" role="region" aria-label="DM Party Inspector"><span class="dm-badge">DM Party Inspector</span><select class="dm-character-switcher" aria-label="Switch inspected character" @change=${(e: Event) => switchDmCharacter(app, (e.target as HTMLSelectElement).value)}>${app.characters.map((c) => html`<option value="${c.id}" ?selected=${c.id === char?.id}>${c.name} (${c.characterClass} Lv ${c.level})</option>`)}</select></div>` : ''}
      ${char ? html`<runefoble-character-card .characterName=${char.name} .characterClass=${`${char.characterClass}${char.level ? ` Lvl ${char.level}` : ''}`} .level=${char.level} .currentHp=${char.currentHp} .maxHp=${char.maxHp} .armorClass=${char.armorClass} .portraitUrl=${char.portraitUrl || ''} .isAiStandIn=${Boolean(char.isAiStandIn)}></runefoble-character-card>
      <button class="btn-toggle-directive" @click=${() => { app.isAbsenteeDirectiveOpen = true; }}>📋 Stance Directives</button>` : html`<div class="empty-state" data-testid="active-character-empty"><p>No character is bound to this session. Choose a character in the session lobby.</p></div>`}
      <runefoble-plugin-slot slot-id="sidebar-tool" .showFallback=${false}></runefoble-plugin-slot>
      <runefoble-plugin-slot slot-id="dice-panel" .showFallback=${false} .pluginProps=${{ 'default-dice-roller': { sessionId: app.sessionId, rollerName: char?.name ?? '' } }}></runefoble-plugin-slot>
    </div>
    <runefoble-watcher-feed .events=${app.events}></runefoble-watcher-feed>
  </div>
  <div class="voice-container">
    <runefoble-voice-controls .isListening=${app.isListening} @voice-toggle=${() => { app.isListening = !app.isListening; }}></runefoble-voice-controls>
  </div>`;
}
