import { LitElement, html, type PropertyValues } from 'lit';
import { customElement, property, query } from 'lit/decorators.js';
import { duplexMeterStyles, duplexControlStyles } from './duplex/styles/index.ts';
import './duplex/settings_panel.ts';

@customElement('runefoble-voice-duplex-controls')
export class RunefobleVoiceDuplexControls extends LitElement {
  @property({ type: String }) sessionId = 'session-default';
  @property({ type: String }) speakerId = 'spk-marcus';
  @property({ type: String }) speakerName = 'Marcus';
  @property({ type: Boolean }) isConnected = true;
  @property({ type: Boolean }) isListening = false;
  @property({ type: Boolean }) isPlaybackActive = false;
  @property({ type: Boolean }) isInterrupted = false;
  @property({ type: Boolean }) isDmMuted = false;
  @property({ type: Boolean }) crossfadeActive = false;
  @property({ type: Number }) micLevel = 0.0;
  @property({ type: Number }) interruptionLatencyMs = 0;
  @property({ type: String }) remainingNarration = '';
  @property({ type: Number }) vadSensitivity = 75;
  @property({ type: Number }) duckingGainDb = -12;
  @property({ type: Boolean }) aecEnabled = true;
  @property({ type: Number }) aecSuppressionDb = 35;
  @property({ type: Boolean }) showSettings = false;

  @query('.duplex-canvas') private canvasElement?: HTMLCanvasElement;
  private animFrameId: number | null = null;
  private simPhase = 0;
  static styles = [duplexMeterStyles, duplexControlStyles];

  firstUpdated() { this.draw(); }
  updated(changed: PropertyValues) {
    if (changed.has('isListening') || changed.has('isInterrupted') || changed.has('isPlaybackActive')) this.draw();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
  }

  public triggerBargeIn(latencyMs = 64, remainingText = 'The goblin warlord...') {
    this.isInterrupted = true;
    this.isDmMuted = true;
    this.isPlaybackActive = false;
    this.crossfadeActive = true;
    this.interruptionLatencyMs = latencyMs;
    this.remainingNarration = remainingText;
    this.dispatchEvent(new CustomEvent('duplex-interrupted', {
      detail: { speakerId: this.speakerId, latencyMs, remainingText },
      bubbles: true, composed: true,
    }));
    setTimeout(() => { this.crossfadeActive = false; }, 200);
    this.draw();
  }

  public resetBargeIn() {
    this.isInterrupted = false;
    this.isDmMuted = false;
    this.crossfadeActive = false;
    this.remainingNarration = '';
    this.draw();
  }

  public toggleSettings() { this.showSettings = !this.showSettings; }
  public toggleMic() {
    this.isListening = !this.isListening;
    this.micLevel = this.isListening ? 0.65 : 0;
    this.draw();
  }

  public handleWebSocketMessage(msg: Record<string, unknown>) {
    if (msg.type === 'voice_duplex_connected') this.isConnected = true;
    else if (msg.type === 'playback_started') {
      this.isPlaybackActive = true; this.isDmMuted = false; this.isInterrupted = false;
    } else if (msg.type === 'barge_in_detected') {
      this.triggerBargeIn(Number(msg.latency_ms || 64), String(msg.remaining_text || ''));
    } else if (msg.type === 'webrtc_stream_mute') this.isDmMuted = Boolean(msg.is_muted);
    else if (msg.type === 'playback_canceled') {
      this.isPlaybackActive = false;
      this.remainingNarration = String(msg.remaining_narration_text || '');
    }
  }

  private draw() {
    const c = this.canvasElement;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    const { width, height } = c;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = '#27272a';
    ctx.beginPath(); ctx.moveTo(0, height / 2); ctx.lineTo(width, height / 2); ctx.stroke();
    if (!this.isListening && !this.isInterrupted) {
      ctx.strokeStyle = '#71717a'; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(0, height / 2); ctx.lineTo(width, height / 2); ctx.stroke();
      ctx.setLineDash([]); return;
    }
    this.simPhase += 0.15;
    ctx.lineWidth = 2;
    ctx.strokeStyle = this.isInterrupted ? '#ef4444' : '#22c55e';
    ctx.beginPath();
    for (let i = 0; i < 48; i++) {
      const x = (i / 47) * width;
      const amp = this.isInterrupted ? 0.8 : (this.micLevel || 0.5);
      const y = height / 2 + Math.sin(i * 0.4 + this.simPhase) * (height / 2.6) * amp;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  render() {
    return html`
      <div class="duplex-panel">
        <div class="header-bar">
          <div class="title-group">
            <span class="badge ${this.isConnected ? 'badge-live' : 'badge-idle'}">
              ${this.isConnected ? '● DUPLEX LIVE' : '○ STANDBY'}
            </span>
            <h3 class="duplex-title">Voice Duplex & Barge-In</h3>
          </div>
          <div class="status-badges">
            ${this.isPlaybackActive ? html`<span class="badge badge-dm">AI DM Speaking</span>` : ''}
            ${this.isDmMuted ? html`<span class="badge badge-muted">DM Audio Canceled</span>` : ''}
            ${this.aecEnabled ? html`<span class="badge badge-live">AEC &gt;${this.aecSuppressionDb}dB</span>` : ''}
          </div>
        </div>
        <div class="visualizer-card">
          <div class="canvas-wrapper">
            <canvas class="duplex-canvas" width="420" height="52" aria-label="Duplex audio visualizer"></canvas>
            ${this.isInterrupted ? html`<div class="barge-in-overlay">⚡ BARGE-IN DETECTED (${this.interruptionLatencyMs}ms)</div>` : ''}
            ${this.crossfadeActive ? html`<div class="crossfade-overlay">20ms Soft Crossfade Active</div>` : ''}
          </div>
          <div class="meters-row">
            <div class="meter-item">
              <div class="meter-label"><span>MIC INPUT</span><span>${Math.round(this.micLevel * 100)}%</span></div>
              <div class="meter-track"><div class="meter-fill" style="width: ${this.micLevel * 100}%;"></div></div>
            </div>
            <div class="meter-item">
              <div class="meter-label"><span>VAD SENSITIVITY</span><span>${this.vadSensitivity}%</span></div>
              <div class="meter-track"><div class="meter-fill warning" style="width: ${this.vadSensitivity}%;"></div></div>
            </div>
            <div class="meter-item">
              <div class="meter-label"><span>DUCKING GAIN</span><span>${this.duckingGainDb} dB</span></div>
              <div class="meter-track"><div class="meter-fill alert" style="width: ${Math.max(0, 100 + this.duckingGainDb * 3)}%;"></div></div>
            </div>
          </div>
        </div>
        ${this.remainingNarration ? html`<div class="narration-tail"><strong>Aborted Narration:</strong> "${this.remainingNarration}"</div>` : ''}
        <div class="actions-row">
          <button class="btn btn-primary" @click=${this.toggleMic} aria-label="Toggle Microphone">
            🎙️ ${this.isListening ? 'Mute Mic' : 'Open Mic'}
          </button>
          <button class="btn btn-warning" @click=${() => this.triggerBargeIn()} aria-label="Simulate Interruption">
            ⚡ Simulate Barge-In
          </button>
          ${this.isInterrupted ? html`<button class="btn btn-secondary" @click=${this.resetBargeIn} aria-label="Reset Interruption">↺ Reset</button>` : ''}
          <button class="btn btn-secondary ${this.showSettings ? 'btn-toggle-active' : ''}" @click=${this.toggleSettings} aria-label="Duplex Settings">
            ⚙️ Settings
          </button>
        </div>
        ${this.showSettings ? html`
          <duplex-settings-panel
            .vadSensitivity=${this.vadSensitivity}
            .duckingGainDb=${this.duckingGainDb}
            .aecEnabled=${this.aecEnabled}
            .aecSuppressionDb=${this.aecSuppressionDb}
            @vad-sensitivity-change=${(e: CustomEvent) => { this.vadSensitivity = e.detail.sensitivity; }}
            @ducking-gain-change=${(e: CustomEvent) => { this.duckingGainDb = e.detail.gainDb; }}
            @aec-toggle=${(e: CustomEvent) => { this.aecEnabled = e.detail.enabled; this.aecSuppressionDb = e.detail.suppressionDb; }}
          ></duplex-settings-panel>` : ''}
      </div>
    `;
  }
}
declare global {
  interface HTMLElementTagNameMap {
    'runefoble-voice-duplex-controls': RunefobleVoiceDuplexControls;
  }
}
