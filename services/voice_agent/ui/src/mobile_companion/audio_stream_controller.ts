import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { audioStyles } from './styles/audio.styles.ts';

@customElement('audio-stream-controller')
export class AudioStreamController extends LitElement {
  @property({ type: String }) channelName = 'Party Voice (Cellular Opus)';
  @property({ type: Number }) sampleRate = 16000;
  @property({ type: Number }) bitrateKbps = 16;
  @property({ type: Number }) packetLoss = 0.0;
  @property({ type: Number }) bandwidthKbps = 120.0;
  @property({ type: Number }) bufferHealthMs = 45;
  @property({ type: Boolean }) isMuted = false;

  static styles = audioStyles;

  private handleBitrateChange(e: Event) {
    const val = Number((e.target as HTMLSelectElement).value);
    this.bitrateKbps = val;
    this.dispatchEvent(
      new CustomEvent('bitrate-change', {
        detail: { bitrateKbps: val },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleMuteToggle() {
    this.isMuted = !this.isMuted;
    this.dispatchEvent(
      new CustomEvent('mute-toggle', {
        detail: { isMuted: this.isMuted },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const isBufferWarn = this.bufferHealthMs < 20;
    const bufferPct = Math.min(100, Math.max(10, (this.bufferHealthMs / 60) * 100));

    return html`
      <div class="audio-status-card" role="region" aria-label="Audio Stream Controller">
        <div class="channel-indicator">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="channel-dot"></span>
            <span class="channel-name">${this.channelName}</span>
          </div>
          <button class="mute-btn ${this.isMuted ? 'muted' : ''}" @click=${this.handleMuteToggle}>
            ${this.isMuted ? '🔇 Unmute' : '🔊 Mute'}
          </button>
        </div>
        <div class="status-line">
          <span class="status-label">Stream Profile</span>
          <span class="status-value">Opus mono ${this.sampleRate / 1000}kHz</span>
        </div>
        <div class="status-line">
          <span class="status-label">Cellular Bitrate</span>
          <div class="bitrate-select-wrapper">
            <select
              class="bitrate-select"
              .value=${String(this.bitrateKbps)}
              @change=${this.handleBitrateChange}
              aria-label="Cellular Bitrate Selector"
            >
              <option value="12">12 kbps (Constrained)</option>
              <option value="16">16 kbps (Mobile Standard)</option>
              <option value="24">24 kbps (High Quality)</option>
            </select>
          </div>
        </div>
        <div class="status-line">
          <span class="status-label">Audio Buffer Health</span>
          <span class="status-value ${isBufferWarn ? 'buffer-warn' : 'buffer-ok'}">
            ${this.bufferHealthMs} ms ${isBufferWarn ? '(Underrun Risk)' : '(Healthy)'}
          </span>
        </div>
        <div class="buffer-bar-container">
          <div class="buffer-bar ${isBufferWarn ? 'warn' : 'ok'}" style="width: ${bufferPct}%"></div>
        </div>
        <div class="status-line">
          <span class="status-label">Packet Loss / Bandwidth</span>
          <span class="status-value">${(this.packetLoss * 100).toFixed(1)}% | ${this.bandwidthKbps.toFixed(0)} kbps</span>
        </div>
      </div>
    `;
  }
}

@customElement('companion-audio-controller')
export class CompanionAudioController extends AudioStreamController {}

declare global {
  interface HTMLElementTagNameMap {
    'audio-stream-controller': AudioStreamController;
    'companion-audio-controller': CompanionAudioController;
  }
}
