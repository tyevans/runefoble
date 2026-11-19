/**
 * No-battlemap-yet empty state (TASK-0906).
 *
 * The session view shows this element in the board area while board_state has no board for
 * the session (the board read answers 404). A caller that may run the session sees a hint to
 * set up a map. The element shows no grid and no tokens, so it never invents board values.
 */

import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export const NO_BOARD_TITLE = 'No battlemap yet';
export const NO_BOARD_PLAYER_TEXT = 'The board shows here when the DM sets up a map for this session.';
export const NO_BOARD_DM_HINT = 'Set up a battlemap for this session to start play on the board.';

@customElement('runefoble-board-empty')
export class RunefobleBoardEmpty extends LitElement {
  /** True when the caller has the `run_session` capability. The element then shows the DM hint. */
  @property({ type: Boolean, attribute: 'can-set-up-map' }) canSetUpMap = false;

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, sans-serif);
      color: var(--rf-text-primary, #1a1a1a);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) dashed var(--rf-border-color, #1a1a1a);
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
      border-left: 4px solid var(--rf-accent-primary, #e63946);
      background: var(--rf-bg-muted, #f4f4f4);
      font-weight: 700;
    }
  `;

  render() {
    return html`<div role="status" aria-live="polite" data-testid="board-empty">
      <h2>${NO_BOARD_TITLE}</h2>
      <p>${NO_BOARD_PLAYER_TEXT}</p>
      ${this.canSetUpMap ? html`<p class="dm-hint" data-testid="board-empty-dm-hint">${NO_BOARD_DM_HINT}</p>` : ''}
    </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-board-empty': RunefobleBoardEmpty;
  }
}
