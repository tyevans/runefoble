import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { badgeStyles } from './styles/badges.styles.ts';

@customElement('connection-status-badge')
export class ConnectionStatusBadge extends LitElement {
  @property({ type: Boolean }) connected = false;
  @property({ type: String }) audioTier = 'mobile_optimized';
  @property({ type: Boolean }) isVibrating = false;
  @property({ type: Number }) latencyMs = 0;

  static styles = badgeStyles;

  private handleReconnect(): void {
    this.dispatchEvent(new CustomEvent('reconnect', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="badge-row" role="status" aria-label="Connection Status">
        <span class="badge ${this.connected ? 'connected' : 'disconnected'}">
          ${this.connected ? 'Online' : 'Offline'}
        </span>
        <span class="badge cellular">${this.audioTier}</span>
        <span class="badge haptic">
          <span class="haptic-pulse-dot ${this.isVibrating ? 'vibrating' : ''}"></span>
          Haptic
        </span>
        ${this.latencyMs > 0
          ? html`<span class="badge latency">${this.latencyMs.toFixed(0)} ms</span>`
          : ''}
        ${!this.connected
          ? html`<button class="reconnect-btn" @click=${this.handleReconnect}>
              Reconnect
            </button>`
          : ''}
      </div>
    `;
  }
}

@customElement('companion-connection-badge')
export class CompanionConnectionBadge extends ConnectionStatusBadge {}

declare global {
  interface HTMLElementTagNameMap {
    'connection-status-badge': ConnectionStatusBadge;
    'companion-connection-badge': CompanionConnectionBadge;
  }
}
