/**
 * No-battlemap-yet empty state (TASK-0906) and the DM set-up control (TASK-0922, TASK-0928).
 *
 * The session view shows this element in the board area while board_state has no board for
 * the session (the board read answers 404). A caller that may run the session sees a hint and
 * the "Set up battlemap" button. The button sends one set-up call that creates the board with the
 * default grid and places one token for each seated character (`setUpSessionBoard`). board_state
 * checks the board and each token.
 *
 * The element shows no grid and no tokens, so it never invents board values. When board_state
 * holds a board after the flow, the element dispatches `board-set-up`, and the host reads the
 * board from the server. A failure before the board exists shows the server message here.
 */

import { AuthConsumerController } from '@runefoble/ui-core';
import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { setUpSessionBoard, type PartySeat } from './board-setup.ts';

export const NO_BOARD_TITLE = 'No battlemap yet';
export const NO_BOARD_PLAYER_TEXT = 'The board shows here when the DM sets up a map for this session.';
export const NO_BOARD_DM_HINT = 'Set up a battlemap for this session to start play on the board.';
export const SET_UP_BATTLEMAP_LABEL = 'Set up battlemap';

/** The detail of `board-set-up`. `failure` is the server message when a token was not placed. */
export interface BoardSetUpDetail {
  sessionId: string;
  failure: string | null;
}

@customElement('runefoble-board-empty')
export class RunefobleBoardEmpty extends LitElement {
  private readonly auth = new AuthConsumerController(this);

  /** True when the caller has the `run_session` capability. The element then shows the DM control. */
  @property({ type: Boolean, attribute: 'can-set-up-map' }) canSetUpMap = false;
  @property({ type: String }) campaignId = '';
  @property({ type: String }) sessionId = '';
  /** The seated characters. Each one gets a token at a free start cell. */
  @property({ type: Array }) seats: PartySeat[] = [];
  /** API base URL put in front of the gateway paths. Empty means the page origin. */
  @property({ type: String }) apiBaseUrl = '';
  @state() private busy = false;
  @state() private errorMessage = '';

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, sans-serif);
      color: var(--rf-text-primary);
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) dashed var(--rf-border-color);
      padding: 32px 20px;
      text-align: center;
      box-sizing: border-box;
    }
    h2 { margin: 0 0 8px; font-size: 1.1rem; font-weight: 800; letter-spacing: 0.02em; }
    p { margin: 0; font-size: 0.9rem; }
    .dm-hint {
      margin-top: 12px;
      display: inline-block;
      padding: 6px 10px;
      border-left: 4px solid var(--rf-accent-primary);
      background: var(--rf-bg-inset);
      font-weight: 700;
    }
    .set-up {
      display: block;
      margin: 16px auto 0;
      padding: 8px 16px;
      font: inherit;
      font-weight: 800;
      color: var(--rf-text-inverse);
      background: var(--rf-border-color);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      cursor: pointer;
    }
    .set-up:hover:not([disabled]) { background: var(--rf-accent-primary); }
    .set-up[disabled] { opacity: 0.6; cursor: progress; }
    .error { margin-top: 12px; color: var(--rf-status-danger); font-weight: 700; }
  `;

  /** Runs the set-up flow once. A second click while it runs does nothing. */
  async setUpBattlemap(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.errorMessage = '';
    const result = await setUpSessionBoard(
      { campaignId: this.campaignId, sessionId: this.sessionId, seats: this.seats },
      { auth: this.auth, apiBase: this.apiBaseUrl },
    );
    this.busy = false;
    if (!result.ok && !result.boardCreated) {
      this.errorMessage = result.message;
      return;
    }
    const detail: BoardSetUpDetail = { sessionId: this.sessionId, failure: result.ok ? null : result.message };
    this.dispatchEvent(new CustomEvent('board-set-up', { detail, bubbles: true, composed: true }));
  }

  private renderDmControl() {
    return html`<p class="dm-hint" data-testid="board-empty-dm-hint">${NO_BOARD_DM_HINT}</p>
      <button class="set-up" type="button" ?disabled=${this.busy} @click=${() => this.setUpBattlemap()}>${SET_UP_BATTLEMAP_LABEL}</button>
      ${this.errorMessage ? html`<p class="error" role="alert">${this.errorMessage}</p>` : ''}`;
  }

  render() {
    return html`<div role="status" aria-live="polite" data-testid="board-empty">
      <h2>${NO_BOARD_TITLE}</h2>
      <p>${NO_BOARD_PLAYER_TEXT}</p>
      ${this.canSetUpMap ? this.renderDmControl() : ''}
    </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-board-empty': RunefobleBoardEmpty;
  }
}
