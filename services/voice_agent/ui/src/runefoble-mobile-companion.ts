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
  @state() private isWhisperBlurred = true;

  private ws: WebSocket | null = null;
  private hapticTimeout: ReturnType<typeof setTimeout> | null = null;

  static styles = mobileCompanionStyles;

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.disconnectWebSocket();
    if (this.hapticTimeout) {
      clearTimeout(this.hapticTimeout);
      this.hapticTimeout = null;
    }
  }

  public triggerHaptic(pattern: number[] = [200, 100, 200], alertType = 'haptic_ping'): void {
    this.isVibrating = true;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try {
        navigator.vibrate(pattern);
      } catch {
        // Fallback gracefully on environments without vibration support
      }
    }
    const totalDuration = pattern.reduce((acc, curr) => acc + curr, 0);
    if (this.hapticTimeout) clearTimeout(this.hapticTimeout);
    this.hapticTimeout = setTimeout(() => {
      this.isVibrating = false;
      this.hapticTimeout = null;
    }, Math.min(totalDuration, 1500));

    this.dispatchEvent(
      new CustomEvent('haptic-pulse', {
        detail: { pattern, alertType },
        bubbles: true,
        composed: true,
      })
    );
  }

  public playAcousticCue(): void {
    if (!this.acousticCueEnabled) return;
    try {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(520, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(780, ctx.currentTime + 0.12);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.35);
      }
    } catch {
      // Graceful fallback on headless or sandboxed environments
    }
  }

  public receiveWhisper(whisper: WhisperMessage, pattern: number[] = [200, 100, 200]): void {
    this.activeWhisper = whisper;
    this.isWhisperBlurred = this.privacyBlur;
    this.playAcousticCue();
    this.triggerHaptic(pattern, 'secret_whisper');
    this.dispatchEvent(
      new CustomEvent('whisper-received', {
        detail: { whisper, isSecret: true },
        bubbles: true,
        composed: true,
      })
    );
  }

  public dismissWhisper(): void {
    const prev = this.activeWhisper;
    this.activeWhisper = null;
    this.dispatchEvent(
      new CustomEvent('whisper-dismissed', {
        detail: { whisper: prev },
        bubbles: true,
        composed: true,
      })
    );
  }

  public toggleWhisperBlur(): void {
    this.isWhisperBlurred = !this.isWhisperBlurred;
    this.dispatchEvent(
      new CustomEvent('whisper-blur-toggled', {
        detail: { blurred: this.isWhisperBlurred },
        bubbles: true,
        composed: true,
      })
    );
  }

  public dismissTurnAlert(): void {
    this.turnAlertActive = false;
    this.dispatchEvent(new CustomEvent('turn-alert-dismissed', { bubbles: true, composed: true }));
  }

  public handleWebSocketMessage(data: any): void {
    if (!data || typeof data !== 'object') return;
    const msgType = data.type || data.action;

    if (msgType === 'haptic_vibration' || msgType === 'haptic_ping') {
      const pattern = data.pattern || data.vibration_pattern || [200, 100, 200];
      this.triggerHaptic(pattern, data.alert_type || 'secret_whisper');
      if (data.whisper) {
        const sender = data.whisper.sender || 'The Watcher';
        const content = data.whisper.body || data.whisper.content || '';
        this.receiveWhisper({ sender, content, timestamp: data.whisper.timestamp }, pattern);
      }
      if (data.notification?.turn_alert || data.turn_alert) {
        this.turnAlertActive = true;
        this.turnAlertText =
          data.notification?.body || data.turn_alert_text || "It's your turn in combat!";
      }
    } else if (msgType === 'whisper' || msgType === 'secret_whisper') {
      const sender = data.sender || 'The Watcher';
      const content = data.content || data.body || '';
      const pattern = data.pattern || data.vibration_pattern || [200, 100, 200];
      this.receiveWhisper({ sender, content, timestamp: data.timestamp }, pattern);
    } else if (msgType === 'audio_profile_adapted') {
      if (data.current_tier) this.audioTier = data.current_tier;
      if (data.profile) {
        if (data.profile.sample_rate) this.sampleRate = data.profile.sample_rate;
        if (data.profile.bitrate_kbps) this.bitrateKbps = data.profile.bitrate_kbps;
      }
      if (data.buffer_ms !== undefined) this.bufferHealthMs = data.buffer_ms;
    } else if (msgType === 'mobile_companion_connected') {
      this.connected = true;
      if (data.audio_profile) {
        if (data.audio_profile.sample_rate) this.sampleRate = data.audio_profile.sample_rate;
        if (data.audio_profile.bitrate_kbps) this.bitrateKbps = data.audio_profile.bitrate_kbps;
        if (data.audio_profile.tier) this.audioTier = data.audio_profile.tier;
      }
      this.notifyConnection(true);
    }
  }

  private notifyConnection(connected: boolean): void {
    this.dispatchEvent(
      new CustomEvent('connection-changed', { detail: { connected }, bubbles: true, composed: true })
    );
  }

  public connectWebSocket(url?: string): void {
    const wsUrl =
      url ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/mobile-companion/${this.sessionId}?user_id=${this.userId}&peer_id=${this.peerId}`
        : '');
    if (!wsUrl || typeof WebSocket === 'undefined') return;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => {
        this.connected = true;
        this.notifyConnection(true);
      };
      this.ws.onclose = () => {
        this.connected = false;
        this.notifyConnection(false);
      };
      this.ws.onerror = () => {
        this.connected = false;
      };
      this.ws.onmessage = (event) => {
        try {
          this.handleWebSocketMessage(JSON.parse(event.data));
        } catch {
          // ignore invalid json
        }
      };
    } catch {
      // ignore connection failures
    }
  }

  public disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.connected = false;
      this.notifyConnection(false);
    }
  }

  public sendTelemetry(packetLoss: number, bandwidthKbps?: number, latencyMs?: number): void {
    this.packetLoss = packetLoss;
    if (bandwidthKbps !== undefined) this.bandwidthKbps = bandwidthKbps;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'mobile_telemetry',
          packet_loss: packetLoss,
          bandwidth_kbps: bandwidthKbps,
          latency_ms: latencyMs,
        })
      );
    }
  }

  private handlePttStart(): void {
    if (this.isTalking) return;
    this.isTalking = true;
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      try {
        navigator.vibrate(15);
      } catch {
        // tactile click fallback
      }
    }
    this.dispatchEvent(
      new CustomEvent('ptt-start', {
        detail: { userId: this.userId, channel: this.channelName, timestamp: new Date().toISOString() },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handlePttEnd(): void {
    if (!this.isTalking) return;
    this.isTalking = false;
    this.dispatchEvent(
      new CustomEvent('ptt-end', {
        detail: { userId: this.userId, channel: this.channelName, timestamp: new Date().toISOString() },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleKeyDown(e: KeyboardEvent): void {
    if (e.code === 'Space' && !e.repeat && !this.isTalking) {
      e.preventDefault();
      this.handlePttStart();
    }
  }

  private handleKeyUp(e: KeyboardEvent): void {
    if (e.code === 'Space' && this.isTalking) {
      e.preventDefault();
      this.handlePttEnd();
    }
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
          <div class="channel-indicator">
            <span class="channel-dot"></span>
            <span class="channel-name">${this.channelName}</span>
          </div>
          <div class="status-line">
            <span class="status-label">Stream Profile</span>
            <span class="status-value">Opus mono ${this.sampleRate / 1000}kHz</span>
          </div>
          <div class="status-line">
            <span class="status-label">Cellular Bitrate</span>
            <span class="status-value">${this.bitrateKbps} kbps</span>
          </div>
          <div class="status-line">
            <span class="status-label">Audio Buffer Health</span>
            <span class="status-value ${this.bufferHealthMs < 20 ? 'buffer-warn' : 'buffer-ok'}">
              ${this.bufferHealthMs} ms ${this.bufferHealthMs < 20 ? '(Underrun Risk)' : '(Healthy)'}
            </span>
          </div>
          <div class="buffer-bar-container">
            <div class="buffer-bar ${this.bufferHealthMs < 20 ? 'warn' : 'ok'}" style="width: ${Math.min(100, Math.max(10, (this.bufferHealthMs / 60) * 100))}%"></div>
          </div>
          <div class="status-line">
            <span class="status-label">Packet Loss / Bandwidth</span>
            <span class="status-value">${(this.packetLoss * 100).toFixed(1)}% | ${this.bandwidthKbps.toFixed(0)} kbps</span>
          </div>
        </div>

        ${this.turnAlertActive
          ? html`<div class="turn-card">
              <div class="turn-title">⚔️ Your Combat Turn!</div>
              <p style="margin: 6px 0;">${this.turnAlertText}</p>
              <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
                <button class="btn" @click=${this.dismissTurnAlert}>Acknowledge</button>
              </div>
            </div>`
          : ''}
        ${this.activeWhisper
          ? html`<div class="whisper-card">
              <div class="whisper-header">
                <span>🤫 Secret Whisper • ${this.activeWhisper.sender}</span>
                <button class="btn btn-xs" @click=${this.toggleWhisperBlur}>
                  ${this.isWhisperBlurred ? '👁️ Reveal' : '🔒 Conceal'}
                </button>
              </div>
              <div class="whisper-body ${this.isWhisperBlurred ? 'content-blurred' : ''}" @click=${this.toggleWhisperBlur} title="${this.isWhisperBlurred ? 'Click to reveal secret whisper' : 'Click to conceal'}">
                "${this.activeWhisper.content}"
                ${this.isWhisperBlurred ? html`<div class="blur-overlay-hint">[Tap to reveal secret whisper]</div>` : ''}
              </div>
              <div class="whisper-actions">
                <button class="btn" @click=${this.dismissWhisper}>Dismiss</button>
              </div>
            </div>`
          : ''}

        <button
          class="btn btn-ptt ${this.isTalking ? 'active' : ''}"
          @mousedown=${this.handlePttStart}
          @mouseup=${this.handlePttEnd}
          @touchstart=${this.handlePttStart}
          @touchend=${this.handlePttEnd}
          @keydown=${this.handleKeyDown}
          @keyup=${this.handleKeyUp}
          tabindex="0"
          aria-label="Push to talk button"
        >
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
