import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './mobile_companion/index.ts';
import type { WhisperMessage } from './mobile_companion/haptic_ping_panel.ts';
import { mobileCompanionStyles } from './runefoble-mobile-companion.styles.ts';

export type { WhisperMessage } from './mobile_companion/haptic_ping_panel.ts';

@customElement('runefoble-mobile-companion')
export class RunefobleMobileCompanion extends LitElement {
  @property({ type: String }) sessionId = 'session_default';
  @property({ type: String }) userId = 'marcus';
  @property({ type: String }) peerId = 'peer_marcus';
  @property({ type: String }) channelName = 'Party Voice (Cellular Opus)';
  @property({ type: Boolean }) connected = false;
  @property({ type: String }) audioTier = 'mobile_optimized';
  @property({ type: Number }) sampleRate = 16000;
  @property({ type: Number }) bitrateKbps = 16;
  @property({ type: Number }) packetLoss = 0.0;
  @property({ type: Number }) bandwidthKbps = 120.0;
  @property({ type: Number }) bufferHealthMs = 45;
  @property({ type: Boolean }) acousticCueEnabled = true;
  @property({ type: Boolean }) privacyBlur = true;
  @property({ type: Object }) activeWhisper: WhisperMessage | null = null;
  @property({ type: Boolean }) turnAlertActive = false;
  @property({ type: String }) turnAlertText = "It's your turn in combat!";

  @state() private isTalking = false;
  @state() private isVibrating = false;
  @state() public isWhisperBlurred = true;

  private ws: WebSocket | null = null;
  private hapticTimeout: ReturnType<typeof setTimeout> | null = null;
  static styles = mobileCompanionStyles;

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.disconnectWebSocket();
    if (this.hapticTimeout) clearTimeout(this.hapticTimeout);
  }

  public triggerHaptic(pattern: number[] = [200, 100, 200], alertType = 'haptic_ping'): void {
    this.isVibrating = true;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try { navigator.vibrate(pattern); } catch { /* ignore */ }
    }
    if (this.hapticTimeout) clearTimeout(this.hapticTimeout);
    this.hapticTimeout = setTimeout(() => { this.isVibrating = false; }, 1500);
    this.dispatchEvent(new CustomEvent('haptic-pulse', { detail: { pattern, alertType }, bubbles: true, composed: true }));
  }

  public playAcousticCue(): void {
    if (!this.acousticCueEnabled) return;
    try {
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      if (Ctx) {
        const c = new Ctx(), osc = c.createOscillator();
        osc.connect(c.destination); osc.start(); osc.stop(c.currentTime + 0.35);
      }
    } catch { /* ignore */ }
  }

  public receiveWhisper(whisper: WhisperMessage, pattern: number[] = [200, 100, 200]): void {
    this.activeWhisper = whisper;
    this.isWhisperBlurred = this.privacyBlur;
    this.playAcousticCue();
    this.triggerHaptic(pattern, 'secret_whisper');
    this.dispatchEvent(new CustomEvent('whisper-received', { detail: { whisper, isSecret: true }, bubbles: true, composed: true }));
  }

  public dismissWhisper(): void {
    const prev = this.activeWhisper;
    this.activeWhisper = null;
    this.dispatchEvent(new CustomEvent('whisper-dismissed', { detail: { whisper: prev }, bubbles: true, composed: true }));
  }

  public toggleWhisperBlur(): void {
    this.isWhisperBlurred = !this.isWhisperBlurred;
    this.dispatchEvent(new CustomEvent('whisper-blur-toggled', { detail: { blurred: this.isWhisperBlurred }, bubbles: true, composed: true }));
  }

  public dismissTurnAlert(): void {
    this.turnAlertActive = false;
    this.dispatchEvent(new CustomEvent('turn-alert-dismissed', { bubbles: true, composed: true }));
  }

  public handleWebSocketMessage(data: any): void {
    if (!data || typeof data !== 'object') return;
    const m = data.type || data.action;
    if (m === 'haptic_vibration' || m === 'haptic_ping') {
      const p = data.pattern || data.vibration_pattern || [200, 100, 200];
      this.triggerHaptic(p, data.alert_type || 'secret_whisper');
      if (data.whisper) this.receiveWhisper({ sender: data.whisper.sender || 'The Watcher', content: data.whisper.body || data.whisper.content || '', timestamp: data.whisper.timestamp }, p);
      if (data.notification?.turn_alert || data.turn_alert) {
        this.turnAlertActive = true;
        this.turnAlertText = data.notification?.body || data.turn_alert_text || "It's your turn in combat!";
      }
    } else if (m === 'whisper' || m === 'secret_whisper') {
      this.receiveWhisper({ sender: data.sender || 'The Watcher', content: data.content || data.body || '', timestamp: data.timestamp }, data.pattern || data.vibration_pattern || [200, 100, 200]);
    } else if (m === 'audio_profile_adapted') {
      if (data.current_tier) this.audioTier = data.current_tier;
      if (data.profile?.sample_rate) this.sampleRate = data.profile.sample_rate;
      if (data.profile?.bitrate_kbps) this.bitrateKbps = data.profile.bitrate_kbps;
      if (data.buffer_ms !== undefined) this.bufferHealthMs = data.buffer_ms;
    } else if (m === 'mobile_companion_connected') {
      this.connected = true;
      if (data.audio_profile?.sample_rate) this.sampleRate = data.audio_profile.sample_rate;
      if (data.audio_profile?.bitrate_kbps) this.bitrateKbps = data.audio_profile.bitrate_kbps;
      if (data.audio_profile?.tier) this.audioTier = data.audio_profile.tier;
      this.dispatchEvent(new CustomEvent('connection-changed', { detail: { connected: true }, bubbles: true, composed: true }));
    }
  }

  public connectWebSocket(url?: string): void {
    const wsUrl = url || (typeof window !== 'undefined' ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/mobile-companion/${this.sessionId}?user_id=${this.userId}&peer_id=${this.peerId}` : '');
    if (!wsUrl || typeof WebSocket === 'undefined') return;
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => { this.connected = true; this.dispatchEvent(new CustomEvent('connection-changed', { detail: { connected: true }, bubbles: true, composed: true })); };
      this.ws.onclose = () => { this.connected = false; this.dispatchEvent(new CustomEvent('connection-changed', { detail: { connected: false }, bubbles: true, composed: true })); };
      this.ws.onerror = () => { this.connected = false; };
      this.ws.onmessage = (e) => { try { this.handleWebSocketMessage(JSON.parse(e.data)); } catch {} };
    } catch {}
  }

  public disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close(); this.ws = null; this.connected = false;
      this.dispatchEvent(new CustomEvent('connection-changed', { detail: { connected: false }, bubbles: true, composed: true }));
    }
  }

  public sendTelemetry(packetLoss: number, bandwidthKbps?: number, latencyMs?: number): void {
    this.packetLoss = packetLoss;
    if (bandwidthKbps !== undefined) this.bandwidthKbps = bandwidthKbps;
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'mobile_telemetry', packet_loss: packetLoss, bandwidth_kbps: bandwidthKbps, latency_ms: latencyMs }));
    }
  }

  private handlePttStart(): void {
    if (this.isTalking) return;
    this.isTalking = true;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') try { navigator.vibrate(15); } catch {}
    this.dispatchEvent(new CustomEvent('ptt-start', { detail: { userId: this.userId, channel: this.channelName, timestamp: new Date().toISOString() }, bubbles: true, composed: true }));
  }

  private handlePttEnd(): void {
    if (!this.isTalking) return;
    this.isTalking = false;
    this.dispatchEvent(new CustomEvent('ptt-end', { detail: { userId: this.userId, channel: this.channelName, timestamp: new Date().toISOString() }, bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="companion-container">
        <div class="companion-header">
          <div class="title-group"><span class="device-icon">📱</span><span class="title-text">Spatial Companion</span></div>
          <connection-status-badge .connected=${this.connected} .audioTier=${this.audioTier} .isVibrating=${this.isVibrating} @reconnect=${() => this.connectWebSocket()}></connection-status-badge>
        </div>
        <audio-stream-controller .channelName=${this.channelName} .sampleRate=${this.sampleRate} .bitrateKbps=${this.bitrateKbps} .bufferHealthMs=${this.bufferHealthMs} .packetLoss=${this.packetLoss} .bandwidthKbps=${this.bandwidthKbps} @bitrate-change=${(e: CustomEvent) => { this.bitrateKbps = e.detail.bitrateKbps; }}></audio-stream-controller>
        <haptic-ping-panel .activeWhisper=${this.activeWhisper} .turnAlertActive=${this.turnAlertActive} .turnAlertText=${this.turnAlertText} .privacyBlur=${this.privacyBlur} .acousticCueEnabled=${this.acousticCueEnabled} @whisper-dismissed=${this.dismissWhisper} @turn-alert-dismissed=${this.dismissTurnAlert} @whisper-blur-toggled=${(e: CustomEvent) => { this.isWhisperBlurred = e.detail.blurred; }}></haptic-ping-panel>
        <button class="btn btn-ptt ${this.isTalking ? 'active' : ''}" @mousedown=${this.handlePttStart} @mouseup=${this.handlePttEnd} @touchstart=${this.handlePttStart} @touchend=${this.handlePttEnd} @keydown=${(e: KeyboardEvent) => { if (e.code === 'Space' && !e.repeat) { e.preventDefault(); this.handlePttStart(); } }} @keyup=${(e: KeyboardEvent) => { if (e.code === 'Space') { e.preventDefault(); this.handlePttEnd(); } }} tabindex="0" aria-label="Push to talk button">
          <span>${this.isTalking ? '🔴' : '🎙️'}</span>
          <span>${this.isTalking ? 'Transmitting (Opus)...' : 'Hold to Speak (Opus)'}</span>
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
