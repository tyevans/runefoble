/**
 * Active Session View (TASK-0643). Renders the live tabletop or the spectator view.
 */

import { html } from 'lit';
import { guard } from 'lit/directives/guard.js';
import type { RunefobleApp } from '../runefoble-app.ts';
import { handleBoardAoEPlace, handleBoardConfirmGhost, handleBoardSpellVFX, handleBoardTokenAction, handleSpeakCommand } from '../vtt-mesh-handlers.ts';
import { switchDmCharacter } from '../app/character-actions.ts';
import { recordBoardMoveTarget, resolveBoardDmAccess } from '../app/board-dm-controls.ts';
import { handleBoardSetUp } from '../app/board-setup-actions.ts';
import { endSession } from '../app/session-actions.ts';
import { openAbsenteeDrawer } from '../app/absentee-actions.ts';
import { findCallerSeat } from '../app/active-character.ts';
import { speakerTokenCell } from '../app/command-bar-context.ts';
import { handleActionVetoed, whisperBarProps } from '../app/whisper-bar-actions.ts';
import { handleVoiceUtterance } from '../app/voice-utterance-actions.ts';

/**
 * The DM ends an active session (TASK-0953). Only a caller with the `run_session` capability sees
 * the control, and only while the session is `active`. The first click asks for a confirm step.
 */
function renderEndSessionControl(app: RunefobleApp, canRunSession: boolean) {
  if (!canRunSession || app.sessionStatus !== 'active') return '';
  if (!app.isEndSessionConfirmOpen) {
    return html`<button class="btn-end-session" @click=${() => { app.isEndSessionConfirmOpen = true; }}>End Session</button>`;
  }
  return html`<div class="end-session-confirm" role="group" aria-label="Confirm end of session">
    <p>End this session for every player? Each player then sees the recap.</p>
    <button class="btn-confirm-end" @click=${() => endSession(app)}>Confirm End</button>
    <button class="btn-cancel-end" @click=${() => { app.isEndSessionConfirmOpen = false; }}>Cancel</button>
  </div>`;
}

/**
 * The DM trap controls for the board. The session id is the board id. Only a caller with the
 * `run_session` capability sees them. The map switch control is removed: no public route lists the
 * battlemaps, so the App Shell cannot offer a map to switch to (TASK-0954).
 */
function renderBoardDmControls(app: RunefobleApp) {
  if (resolveBoardDmAccess(app.campaignCapabilities) !== 'allowed') return '';
  return html`<div class="dm-board-controls" role="region" aria-label="DM Board Controls">
    <runefoble-dm-trap-controls .boardId=${app.sessionId} .targetX=${app.boardTarget?.targetX ?? null} .targetY=${app.boardTarget?.targetY ?? null}></runefoble-dm-trap-controls>
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
  if (app.boardKind === 'no_board') return html`<runefoble-board-empty ?can-set-up-map=${canRunSession} .campaignId=${app.campaignId} .sessionId=${app.sessionId} .seats=${guard([app.sessionSeats], () => app.sessionSeats)} @board-set-up=${(e: CustomEvent) => handleBoardSetUp(app, e)}></runefoble-board-empty>`;
  return html`<runefoble-board .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${guard([app.tokens], () => app.tokens)} .fogOfWar=${true} .websocketUrl=${app.getWebSocketUrl()} @token-action=${(e: CustomEvent) => handleBoardTokenAction(e, app.sessionSocket.current)} @aoe-place=${(e: CustomEvent) => handleBoardAoEPlace(e, app.sessionSocket.current)} @spell-vfx-triggered=${(e: CustomEvent) => handleBoardSpellVFX(e, app.sessionSocket.current)} @confirm-ghost=${(e: CustomEvent) => handleBoardConfirmGhost(e, app.sessionSocket.current)} @move-token=${(e: CustomEvent) => recordBoardMoveTarget(app, e)} @tokens-changed=${(e: CustomEvent) => { app.shownTokens = e.detail.tokens; }}></runefoble-board>
      ${renderBoardDmControls(app)}`;
}

/**
 * Renders the live tabletop (party mode) or the spectator view for an active session.
 * An ended session shows the recap of its chronicle to every caller (TASK-0953).
 */
export function renderSessionActive(app: RunefobleApp) {
  const char = app.activeCharacter ?? app.resolveActiveCharacter(app.campaignId);
  const canRunSession = Boolean(app.campaignCapabilities?.run_session);
  // The stand-in state is the caller seat's, read from game_session (TASK-0974).
  const isStandIn = findCallerSeat(app.sessionParticipants, app.currentUserId)?.isStandInActive === true;
  if (app.sessionStatus === 'ended') {
    return html`<runefoble-session-recap .sessionTitle=${app.sessionTitle} .entries=${app.events}></runefoble-session-recap>`;
  }
  if (app.viewMode === 'spectator') {
    return html`<runefoble-spectator-view .sessionId=${app.sessionId} .cols=${app.boardCols} .rows=${app.boardRows} .tokens=${app.tokens} .atmosphere=${app.atmosphere} .chronicle=${app.events}></runefoble-spectator-view>`;
  }
  return html`<div class="layout-grid">
    <div class="board-column">
      <runefoble-plugin-slot slot-id="hud-widget" .showFallback=${false}></runefoble-plugin-slot>
      ${renderBoardArea(app, canRunSession)}
    </div>
    <div class="character-column">
      ${renderEndSessionControl(app, canRunSession)}
      ${canRunSession ? html`<div class="dm-party-inspector" role="region" aria-label="DM Party Inspector"><span class="dm-badge">DM Party Inspector</span><select class="dm-character-switcher" aria-label="Switch inspected character" @change=${(e: Event) => switchDmCharacter(app, (e.target as HTMLSelectElement).value)}>${app.characters.map((c) => html`<option value="${c.id}" ?selected=${c.id === char?.id}>${c.name} (${c.characterClass} Lv ${c.level})</option>`)}</select></div>` : ''}
      ${char ? html`<runefoble-character-card .characterName=${char.name} .characterClass=${`${char.characterClass}${char.level ? ` Lvl ${char.level}` : ''}`} .level=${char.level} .currentHp=${char.currentHp} .maxHp=${char.maxHp} .armorClass=${char.armorClass} .portraitUrl=${char.portraitUrl || ''} .isAiStandIn=${isStandIn}></runefoble-character-card>
      ${isStandIn ? html`<button class="btn-toggle-directive" @click=${() => openAbsenteeDrawer(app)}>📋 Stance Directives</button>` : ''}` : html`<div class="empty-state" data-testid="active-character-empty"><p>No character is bound to this session. Choose a character in the session lobby.</p></div>`}
      <runefoble-plugin-slot slot-id="sidebar-tool" .showFallback=${false} .pluginProps=${guard([app.sessionId, app.campaignId], () => whisperBarProps(app.sessionId, app.campaignId))} @action-vetoed=${handleActionVetoed}></runefoble-plugin-slot>
      <runefoble-plugin-slot slot-id="dice-panel" .showFallback=${false} .pluginProps=${guard([app.sessionId, char?.name ?? ''], () => ({ 'default-dice-roller': { sessionId: app.sessionId, rollerName: char?.name ?? '' } }))}></runefoble-plugin-slot>
    </div>
    <runefoble-watcher-feed .events=${app.events}></runefoble-watcher-feed>
  </div>
  <div class="voice-container">
    ${renderCommandBar(app, char)}
    <runefoble-voice-controls .sending=${app.voiceUtterance.sending} .transcript=${app.voiceUtterance.transcript} .watcherError=${app.voiceUtterance.watcherError} .uploadError=${app.voiceUtterance.uploadError} @voice-utterance=${(e: CustomEvent) => handleVoiceUtterance(app, e, char?.id)}></runefoble-voice-controls>
  </div>`;
}

/**
 * The typed command bar (TASK-0945). The speaker is the active character. Its token and cell
 * come from the tokens that the board shows. Without a board the bar has no token and is disabled.
 */
function renderCommandBar(app: RunefobleApp, char: { id: string; name: string } | null) {
  const cell = speakerTokenCell(app.boardKind === 'board' ? app.shownTokens : [], char?.id);
  return html`<runefoble-command-bar .sessionId=${app.sessionId} .campaignId=${app.campaignId} .speakerId=${char?.id ?? ''} .speakerName=${char?.name ?? ''} .tokenId=${cell.tokenId} .fromX=${cell.fromX} .fromY=${cell.fromY} .gridCols=${app.boardCols} .gridRows=${app.boardRows} .status=${app.commandStatus} @speak-command=${(e: CustomEvent) => handleSpeakCommand(app, e)}></runefoble-command-bar>`;
}
