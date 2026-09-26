import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, query, state } from 'lit/decorators.js';
import { renderAudioWaveform } from './waveform-visualizer.ts';

export type WebRTCConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed';
export type BandwidthQuality = 'good' | 'low' | 'degraded';

@customElement('runefoble-voice-controls')
export class RunefobleVoiceControls extends LitElement {
  @property({ type: Boolean }) isListening = false;
  @property({ type: Boolean }) disabled = false;
  @property({ type: String }) channelName = 'Collaborative Voice Channel';
  @property({ type: String }) connectionState: WebRTCConnectionState = 'disconnected';
  @property({ type: String }) bandwidthQuality: BandwidthQuality = 'good';
  @property({ type: Number }) bitrateKbps = 64;
  @property({ type: Number }) packetsLost = 0;
  @property({ type: Number }) latencyMs = 24;
  @property({ type: Array }) activeFilters: string[] = [];
  @property({ type: Boolean }) simulated = false;

  @state() private audioLevel = 0;
  @query('.waveform-canvas') private canvasElement?: HTMLCanvasElement;

  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private mediaStream: MediaStream | null = null;
  private animFrameId: number | null = null;
  private simPhase = 0;

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary, #121212);
    }
    .voice-control-panel {
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-sizing: border-box;
      transition: background-color 0.2s ease, border-color 0.2s ease;
    }
    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .channel-header {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .status-indicator {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background-color: var(--rf-text-muted, #4b5563);
      display: inline-block;
      transition: background-color 0.2s ease;
    }
    .status-indicator.live {
      background-color: var(--rf-accent-primary, #e63946);
      box-shadow: 0 0 6px var(--rf-accent-primary, #e63946);
      animation: pulse-dot 1.5s infinite;
    }
    @keyframes pulse-dot {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .channel-title {
      font-weight: 700;
      font-size: 1rem;
      color: var(--rf-text-primary, #121212);
    }
    .status-badges {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .badge {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      border-radius: var(--rf-border-radius, 0px);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-webrtc.connected { background: var(--rf-bg-surface, #ffffff); color: var(--rf-accent-secondary, #1d3557); }
    .badge-webrtc.disconnected { background: var(--rf-bg-canvas, #f8f9fa); color: var(--rf-text-muted, #4b5563); }
    .badge-webrtc.connecting, .badge-webrtc.reconnecting { background: var(--rf-accent-tertiary, #ffb703); color: #121212; }
    .badge-webrtc.failed { background: var(--rf-accent-primary, #e63946); color: #ffffff; }
    .badge-warning { background: var(--rf-accent-primary, #e63946); color: #ffffff; animation: pulse-warning 1.8s infinite; }
    .badge-dsp { background: var(--rf-accent-tertiary, #ffb703); color: #121212; }
    @keyframes pulse-warning {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.75; }
    }
    .main-controls-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    .visualizer-wrapper {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
      min-width: 260px;
    }
    .canvas-container {
      background: #121212;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      border-radius: var(--rf-border-radius, 0px);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex: 1;
      height: 44px;
    }
    .waveform-canvas {
      display: block;
      width: 100%;
      height: 100%;
    }
    .metrics-panel {
      display: flex;
      flex-direction: column;
      gap: 2px;
      font-size: 0.72rem;
      font-family: monospace;
      font-weight: 700;
      color: var(--rf-text-muted, #4b5563);
      min-width: 90px;
    }
    .mic-button {
      background: var(--rf-accent-primary, #e63946);
      color: var(--rf-color-light, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      padding: 10px 18px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: inherit;
      white-space: nowrap;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .mic-button:hover:not(:disabled) {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }
    .mic-button:active:not(:disabled) {
      transform: translate(1px, 1px);
      box-shadow: 1px 1px 0px #121212;
    }
    .mic-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .mic-button.listening { background: var(--rf-accent-tertiary, #ffb703); color: #121212; }
    .panel-instruction {
      font-size: 0.8rem;
      color: var(--rf-text-muted, #4b5563);
    }
  `;

  firstUpdated() {
    this.renderWaveform();
  }

  updated(changed: PropertyValues) {
    if (changed.has('isListening')) {
      if (this.isListening) {
        if (this.connectionState === 'disconnected') {
          this.connectionState = 'connected';
        }
        this.startAudio();
      } else {
        this.stopAudio();
      }
      this.emitVoiceState();
    }
    if (changed.has('connectionState') || changed.has('bandwidthQuality') || changed.has('activeFilters')) {
      this.emitVoiceState();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.stopAudio();
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
  }

  private emitVoiceState() {
    this.dispatchEvent(
      new CustomEvent('voice-state', {
        detail: {
          isListening: this.isListening,
          connectionState: this.connectionState,
          bandwidthQuality: this.bandwidthQuality,
          activeFilters: this.activeFilters,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private async startAudio() {
    if (!this.simulated && typeof window !== 'undefined' && window.navigator?.mediaDevices?.getUserMedia) {
      try {
        const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (AudioCtxClass) {
          this.audioCtx = new AudioCtxClass();
          this.analyser = this.audioCtx.createAnalyser();
          this.analyser.fftSize = 256;
          this.mediaStream = await window.navigator.mediaDevices.getUserMedia({ audio: true });
          const source = this.audioCtx.createMediaStreamSource(this.mediaStream);
          source.connect(this.analyser);
        }
      } catch {
        // Fallback gracefully to simulated render loop
      }
    }
    this.startRenderLoop();
  }

  private stopAudio() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.audioCtx && this.audioCtx.state !== 'closed') {
      this.audioCtx.close().catch(() => {});
      this.audioCtx = null;
      this.analyser = null;
    }
    this.audioLevel = 0;
    this.renderWaveform();
  }

  private startRenderLoop() {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
    }
    const loop = () => {
      if (!this.isListening) {
        this.renderWaveform();
        return;
      }
      this.renderWaveform();
      this.animFrameId = requestAnimationFrame(loop);
    };
    this.animFrameId = requestAnimationFrame(loop);
  }

  private renderWaveform() {
    const canvas = this.canvasElement;
    if (!canvas) return;

    const metrics = renderAudioWaveform({
      canvas,
      isListening: this.isListening,
      analyser: this.analyser,
      activeFilters: this.activeFilters,
      simPhase: this.simPhase,
    });

    this.simPhase = metrics.nextSimPhase;
    this.audioLevel = metrics.level;

    if (this.isListening) {
      this.dispatchEvent(
        new CustomEvent('voice-level', {
          detail: { level: metrics.level, peak: metrics.peak },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  private _handleToggle() {
    if (this.disabled) return;
    this.dispatchEvent(
      new CustomEvent('voice-toggle', {
        detail: { isListening: !this.isListening },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const isDegraded = this.bandwidthQuality === 'low' || this.bandwidthQuality === 'degraded' || this.packetsLost > 5;

    return html`
      <div class="voice-control-panel">
        <div class="header-row">
          <div class="channel-header">
            <span class="status-indicator ${this.isListening ? 'live' : ''}"></span>
            <strong class="channel-title">${this.channelName}</strong>
          </div>
          <div class="status-badges">
            <span class="badge badge-webrtc ${this.connectionState}">
              ${this.connectionState === 'connected'
                ? '● WebRTC Live'
                : this.connectionState === 'connecting' || this.connectionState === 'reconnecting'
                  ? '⟳ Reconnecting...'
                  : '○ Standby'}
            </span>
            ${isDegraded
              ? html`<span class="badge badge-warning">
                  ⚠️ Low Bandwidth (${this.bitrateKbps}kbps, ${this.packetsLost} drops)
                </span>`
              : ''}
            ${this.activeFilters.map(
              (filter) => html`<span class="badge badge-dsp">DSP: ${filter}</span>`
            )}
          </div>
        </div>

        <div class="main-controls-row">
          <div class="visualizer-wrapper">
            <div class="canvas-container">
              <canvas
                class="waveform-canvas"
                width="320"
                height="44"
                aria-label="Real-time WebRTC audio waveform"
              ></canvas>
            </div>
            <div class="metrics-panel">
              <span>BITRATE: ${this.bitrateKbps}k</span>
              <span>LATENCY: ${this.latencyMs}ms</span>
              <span>LEVEL: ${Math.round(this.audioLevel * 100)}%</span>
            </div>
          </div>

          <button
            class="mic-button ${this.isListening ? 'listening' : ''}"
            ?disabled=${this.disabled}
            @click=${this._handleToggle}
            aria-label="${this.isListening ? 'Mute microphone' : 'Start speaking'}"
          >
            🎙️ ${this.isListening ? 'Streaming (Mute)' : 'Push to Talk'}
          </button>
        </div>

        <div class="panel-instruction">
          Speak naturally: "Move my warrior to the chest", "Cast cure wounds on Valeros", "What does the altar look like?"
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-voice-controls': RunefobleVoiceControls;
  }
}
