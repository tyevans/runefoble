import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { whisperStyles } from './styles/whisper.styles.ts';

export interface WhisperMessage {
  sender: string;
  content: string;
  timestamp?: string;
}

@customElement('haptic-ping-panel')
export class HapticPingPanel extends LitElement {
  @property({ type: Object }) activeWhisper: WhisperMessage | null = null;
  @property({ type: Boolean }) turnAlertActive = false;
  @property({ type: String }) turnAlertText = "It's your turn in combat!";
  @property({ type: Boolean }) privacyBlur = true;
  @property({ type: Boolean }) acousticCueEnabled = true;
  @state() public isWhisperBlurred = true;

  static styles = whisperStyles;

  public playAcousticCue(): void {
    if (!this.acousticCueEnabled) return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx(), osc = ctx.createOscillator(), gain = ctx.createGain();
        osc.frequency.setValueAtTime(520, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(780, ctx.currentTime + 0.12);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.connect(gain); gain.connect(ctx.destination);
        osc.start(); osc.stop(ctx.currentTime + 0.35);
      }
    } catch { /* headless fallback */ }
  }

  public triggerHaptic(pattern: number[] = [200, 100, 200], alertType = 'haptic_ping'): void {
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try { navigator.vibrate(pattern); } catch { /* unsupported */ }
    }
    this.dispatchEvent(new CustomEvent('haptic-pulse', {
      detail: { pattern, alertType },
      bubbles: true,
      composed: true,
    }));
  }

  public toggleWhisperBlur(): void {
    this.isWhisperBlurred = !this.isWhisperBlurred;
    this.dispatchEvent(new CustomEvent('whisper-blur-toggled', {
      detail: { blurred: this.isWhisperBlurred },
      bubbles: true,
      composed: true,
    }));
  }

  public dismissWhisper(): void {
    const prev = this.activeWhisper;
    this.activeWhisper = null;
    this.dispatchEvent(new CustomEvent('whisper-dismissed', {
      detail: { whisper: prev },
      bubbles: true,
      composed: true,
    }));
  }

  public dismissTurnAlert(): void {
    this.turnAlertActive = false;
    this.dispatchEvent(new CustomEvent('turn-alert-dismissed', { bubbles: true, composed: true }));
  }

  render() {
    return html`
      ${this.turnAlertActive
        ? html`<div class="turn-card" role="alert">
            <div class="turn-title">⚔️ Your Combat Turn!</div>
            <p style="margin: 6px 0;">${this.turnAlertText}</p>
            <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
              <button class="btn" @click=${this.dismissTurnAlert}>Acknowledge</button>
            </div>
          </div>`
        : ''}
      ${this.activeWhisper
        ? html`<div class="whisper-card" role="region" aria-label="Secret Whisper">
            <div class="whisper-header">
              <span>🤫 Secret Whisper • ${this.activeWhisper.sender}</span>
              <button class="btn btn-xs" @click=${this.toggleWhisperBlur}>
                ${this.isWhisperBlurred ? '👁️ Reveal' : '🔒 Conceal'}
              </button>
            </div>
            <div
              class="whisper-body ${this.isWhisperBlurred ? 'content-blurred' : ''}"
              @click=${this.toggleWhisperBlur}
              title="${this.isWhisperBlurred ? 'Click to reveal secret whisper' : 'Click to conceal'}"
            >
              "${this.activeWhisper.content}"
              ${this.isWhisperBlurred ? html`<div class="blur-overlay-hint">[Tap to reveal secret whisper]</div>` : ''}
            </div>
            <div class="whisper-actions">
              <button class="btn" @click=${this.dismissWhisper}>Dismiss</button>
            </div>
          </div>`
        : ''}
    `;
  }
}

@customElement('companion-haptic-panel')
export class CompanionHapticPanel extends HapticPingPanel {}

declare global {
  interface HTMLElementTagNameMap {
    'haptic-ping-panel': HapticPingPanel;
    'companion-haptic-panel': CompanionHapticPanel;
  }
}
