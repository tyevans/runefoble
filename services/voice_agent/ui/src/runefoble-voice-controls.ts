import { LitElement, html, type PropertyValues } from 'lit';
import { customElement, property, query, state } from 'lit/decorators.js';
import { renderAudioWaveform } from './waveform-visualizer.ts';
import { voiceControlsStyles } from './runefoble-voice-controls.styles.ts';

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

  static styles = voiceControlsStyles;


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
