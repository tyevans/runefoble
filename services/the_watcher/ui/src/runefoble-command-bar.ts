/**
 * `<runefoble-command-bar>`: the typed command bar of the session view (TASK-0945).
 *
 * The player types the same command that the player can speak. Send or Enter emits
 * `speak-command` with the body of `POST /api/v1/watcher/speak-and-act`. The element calls no
 * network. The host posts the body and sets `status` to show the reply or the error. A move
 * reply stages a ghost preview on the board socket, and the player confirms it on the board.
 * Without the speaker's token cell the input is disabled. ADR-0004, ADR-0013, ADR-0022 (c).
 */

import { LitElement, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  buildSpeakCommandBody,
  hasTokenCell,
  IDLE_COMMAND_STATUS,
  NO_TOKEN_MESSAGE,
  type CommandBarContext,
  type CommandBarStatus,
} from './command-bar-body.ts';
import { commandBarStyles } from './runefoble-command-bar.styles.ts';

@customElement('runefoble-command-bar')
export class RunefobleCommandBar extends LitElement {
  static styles = commandBarStyles;

  @property({ type: String }) sessionId = '';
  @property({ type: String }) campaignId = '';
  @property({ type: String }) speakerId = '';
  @property({ type: String }) speakerName = '';
  @property({ type: String }) tokenId: string | null = null;
  @property({ type: Number }) fromX: number | null = null;
  @property({ type: Number }) fromY: number | null = null;
  @property({ type: Number }) gridCols = 12;
  @property({ type: Number }) gridRows = 12;
  /** What the bar shows under the input. The host sets it for each sent command. */
  @property({ type: Object }) status: CommandBarStatus = IDLE_COMMAND_STATUS;

  @state() private typed = '';

  private context(): CommandBarContext {
    return {
      sessionId: this.sessionId,
      campaignId: this.campaignId,
      speakerId: this.speakerId,
      speakerName: this.speakerName,
      tokenId: this.tokenId,
      fromX: this.fromX,
      fromY: this.fromY,
      gridCols: this.gridCols,
      gridRows: this.gridRows,
    };
  }

  /** A reply clears the typed text. An error keeps it, so the player can send it again. */
  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('status') && this.status.kind === 'reply') this.typed = '';
  }

  private submit(e: Event) {
    e.preventDefault();
    if (this.status.kind === 'sending') return;
    const body = buildSpeakCommandBody(this.context(), this.typed);
    if (!body) return;
    this.dispatchEvent(new CustomEvent('speak-command', { detail: body, bubbles: true, composed: true }));
  }

  private renderStatus(hasToken: boolean) {
    if (!hasToken) return html`<p class="status notice" role="status">${NO_TOKEN_MESSAGE}</p>`;
    switch (this.status.kind) {
      case 'sending':
        return html`<p class="status sending" role="status">Sending the command...</p>`;
      case 'reply':
        return html`<p class="status reply" role="status">${this.status.text}</p>`;
      case 'error':
        return html`<p class="status error" role="alert">${this.status.text}</p>`;
      default:
        return nothing;
    }
  }

  render() {
    const hasToken = hasTokenCell(this.context());
    const sending = this.status.kind === 'sending';
    const canSend = hasToken && !sending && this.typed.trim() !== '';
    return html`
      <form class="bar" aria-label="Typed command" @submit=${(e: Event) => this.submit(e)}>
        <label class="label" for="command-input">Command</label>
        <input
          id="command-input"
          class="input"
          type="text"
          autocomplete="off"
          placeholder=${hasToken ? 'Type a command, for example: move 2 squares west' : NO_TOKEN_MESSAGE}
          .value=${this.typed}
          ?disabled=${!hasToken}
          @input=${(e: Event) => { this.typed = (e.target as HTMLInputElement).value; }}
        />
        <button class="send" type="submit" ?disabled=${!canSend}>Send</button>
      </form>
      ${this.renderStatus(hasToken)}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-command-bar': RunefobleCommandBar;
  }
}
