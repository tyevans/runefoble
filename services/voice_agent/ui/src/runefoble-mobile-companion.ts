import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { mobileCompanionStyles } from './runefoble-mobile-companion.styles.ts';

export interface WhisperMessage {
  sender: string;
  content: string;
  timestamp?: string;
}

@customElement('runefoble-mobile-companion')
export class RunefobleMobileCompanion extends LitElement {
  @property({ type: String }) sessionId = 'session_default';
  @property({ type: String }) userId = 'marcus';
  @property({ type: String }) peerId = 'peer_marcus';
  @property({ type: Boolean }) connected = false;
  @property({ type: String }) audioTier = 'mobile_optimized';
  @property({ type: Number }) sampleRate = 16000;
  @property({ type: Number }) bitrateKbps = 16;
  @property({ type: Number }) packetLoss = 0.0;
  @property({ type: Number }) bandwidthKbps = 120.0;
  @property({ type: Object }) activeWhisper: WhisperMessage | null = null;
  @property({ type: Boolean }) turnAlertActive = false;
  @property({ type: String }) turnAlertText = "It's your turn in combat!";

  @state() private isTalking = false;
  @state() private isVibrating = false;

  static styles = mobileCompanionStyles;

  public triggerHaptic(pattern: number[] = [200, 100, 200]): void {
    this.isVibrating = true;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try {
        navigator.vibrate(pattern);
      } catch {
        // Fallback gracefully on environments without vibration support
      }
    }
    const totalDuration = pattern.reduce((acc, curr) => acc + curr, 0);
    setTimeout(() => {
      this.isVibrating = false;
    }, Math.min(totalDuration, 1500));

    this.dispatchEvent(
      new CustomEvent('haptic-pulse', {
        detail: { pattern },
        bubbles: true,
        composed: true,
      })
    );
  }

  public receiveWhisper(whisper: WhisperMessage, pattern: number[] = [200, 100, 200]): void {
    this.activeWhisper = whisper;
    this.triggerHaptic(pattern);
  }

  public dismissWhisper(): void {
    this.activeWhisper = null;
  }

  public dismissTurnAlert(): void {
    this.turnAlertActive = false;
  }

  private handlePttStart(): void {
    this.isTalking = true;
    this.dispatchEvent(
      new CustomEvent('ptt-start', {
        detail: { userId: this.userId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handlePttEnd(): void {
    this.isTalking = false;
    this.dispatchEvent(
      new CustomEvent('ptt-end', {
        detail: { userId: this.userId },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="companion-container">
        <div class="companion-header">
          <div class="title-group">
            <span class="device-icon">📱</span>
            <span class="title-text">Spatial Companion</span>
          </div>
          <div class="badge-row">
            <span class="badge ${this.connected ? 'connected' : 'disconnected'}">
              ${this.connected ? 'Online' : 'Offline'}
            </span>
            <span class="badge cellular">${this.audioTier}</span>
            <span class="badge haptic">
              <span class="haptic-pulse-dot ${this.isVibrating ? 'vibrating' : ''}"></span>
              Haptic
            </span>
          </div>
        </div>

        <div class="audio-status-card">
          <div class="status-line">
            <span class="status-label">Stream Profile</span>
            <span class="status-value">Opus mono ${this.sampleRate / 1000}kHz</span>
          </div>
          <div class="status-line">
            <span class="status-label">Cellular Bitrate</span>
            <span class="status-value">${this.bitrateKbps} kbps</span>
          </div>
          <div class="status-line">
            <span class="status-label">Packet Loss / Bandwidth</span>
            <span class="status-value">
              ${(this.packetLoss * 100).toFixed(1)}% | ${this.bandwidthKbps.toFixed(0)} kbps
            </span>
          </div>
        </div>

        ${this.turnAlertActive
          ? html`
              <div class="turn-card">
                <div class="turn-title">⚔️ Your Combat Turn!</div>
                <p style="margin: 6px 0;">${this.turnAlertText}</p>
                <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
                  <button class="btn" @click=${this.dismissTurnAlert}>Acknowledge</button>
                </div>
              </div>
            `
          : ''}
        ${this.activeWhisper
          ? html`
              <div class="whisper-card">
                <div class="whisper-header">
                  <span>🤫 Secret Whisper • ${this.activeWhisper.sender}</span>
                </div>
                <div class="whisper-body">
                  "${this.activeWhisper.content}"
                </div>
                <div class="whisper-actions">
                  <button class="btn" @click=${this.dismissWhisper}>Dismiss</button>
                </div>
              </div>
            `
          : ''}

        <button
          class="btn btn-ptt ${this.isTalking ? 'active' : ''}"
          @mousedown=${this.handlePttStart}
          @mouseup=${this.handlePttEnd}
          @touchstart=${this.handlePttStart}
          @touchend=${this.handlePttEnd}
        >
          ${this.isTalking ? '🎙️ Transmitting...' : 'Hold to Speak (Opus)'}
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-mobile-companion': RunefobleMobileCompanion;
  }
}
