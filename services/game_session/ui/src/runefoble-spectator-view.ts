import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export interface SpectatorToken {
  id: string;
  name: string;
  x: number;
  y: number;
  conditions?: string[];
  color?: string;
  isAiControlled?: boolean;
  isActiveTurn?: boolean;
}

export interface SpectatorAtmosphere {
  location_name: string;
  lighting: string;
  mood: string;
  description: string;
  ambient_audio_prompt?: string;
}

export interface SpectatorChronicleItem {
  id: string;
  speaker: string;
  text: string;
  timestamp: string;
  action_type?: string;
}

@customElement('runefoble-spectator-view')
export class RunefobleSpectatorView extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary, #121212);
      background: var(--rf-bg-canvas, #f8f9fa);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      box-sizing: border-box;
      padding: 16px;
      gap: 16px;
      width: 100%;
      max-width: 1080px;
      margin: 0 auto;
      user-select: none;
      transition: background-color 0.2s ease, border-color 0.2s ease;
    }

    :host([transparent-mode]) {
      background: transparent;
      box-shadow: none;
    }

    /* Top Overlay Header */
    .stream-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding: 10px 16px;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      flex-wrap: wrap;
      gap: 12px;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .live-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--rf-color-red, #e63946);
      color: var(--rf-color-light, #ffffff);
      font-size: 0.75rem;
      font-weight: 800;
      padding: 3px 8px;
      letter-spacing: 0.5px;
      border: 1px solid var(--rf-border-color, #121212);
    }

    .live-dot {
      width: 8px;
      height: 8px;
      background: #ffffff;
      border-radius: 50%;
      animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    .session-title {
      font-size: 1.05rem;
      font-weight: 900;
      letter-spacing: -0.3px;
    }

    .round-pill {
      background: var(--rf-color-blue, #1d3557);
      color: #ffffff;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 3px 8px;
      border: 1px solid var(--rf-border-color, #121212);
    }

    /* Scene Atmosphere Bar */
    .atmosphere-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding: 8px 14px;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-size: 0.85rem;
      flex-wrap: wrap;
    }

    .scene-tag {
      font-weight: 800;
      color: var(--rf-color-blue, #1d3557);
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .scene-meta {
      color: var(--rf-text-muted, #4b5563);
      font-size: 0.8rem;
    }

    .audio-visualizer {
      display: inline-flex;
      align-items: flex-end;
      gap: 3px;
      height: 14px;
      margin-left: auto;
    }

    .audio-bar {
      width: 3px;
      background: var(--rf-color-yellow, #ffb703);
      border: 1px solid var(--rf-border-color, #121212);
      animation: audioJump 1.2s ease-in-out infinite alternate;
    }
    .audio-bar:nth-child(2) { animation-delay: 0.2s; height: 10px; }
    .audio-bar:nth-child(3) { animation-delay: 0.4s; height: 14px; }
    .audio-bar:nth-child(4) { animation-delay: 0.1s; height: 8px; }

    @keyframes audioJump {
      0% { height: 4px; }
      100% { height: 14px; }
    }

    /* Board Area */
    .board-container {
      display: flex;
      justify-content: center;
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      padding: 18px;
      overflow-x: auto;
    }

    .grid {
      display: grid;
      gap: 2px;
      background: var(--rf-border-color, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      pointer-events: none; /* Read-only: no dragging or clicking for spectators */
    }

    .cell {
      width: 52px;
      height: 52px;
      background: var(--rf-bg-canvas, #f8f9fa);
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
    }

    .token {
      width: 44px;
      height: 44px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: 800;
      font-size: 0.75rem;
      position: relative;
      transition: transform 0.25s ease;
    }

    .token.active-turn {
      outline: 3px solid var(--rf-color-red, #e63946);
      outline-offset: 2px;
    }

    .token-label {
      font-size: 0.65rem;
      background: rgba(18, 18, 18, 0.85);
      color: #ffffff;
      padding: 1px 3px;
      white-space: nowrap;
      position: absolute;
      bottom: -8px;
      left: 50%;
      transform: translateX(-50%);
      pointer-events: none;
      border: 1px solid var(--rf-border-color, #121212);
    }

    .token-condition {
      position: absolute;
      top: -6px;
      right: -6px;
      background: var(--rf-color-yellow, #ffb703);
      color: var(--rf-color-dark, #121212);
      border: 1px solid var(--rf-border-color, #121212);
      font-size: 0.55rem;
      font-weight: 800;
      padding: 1px 3px;
    }

    /* Chronicle Ticker at bottom */
    .chronicle-ticker {
      display: flex;
      align-items: stretch;
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      min-height: 48px;
      overflow: hidden;
    }

    .ticker-label {
      background: var(--rf-color-yellow, #ffb703);
      color: var(--rf-color-dark, #121212);
      font-weight: 900;
      font-size: 0.75rem;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 6px;
      border-right: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      white-space: nowrap;
    }

    .ticker-stream {
      flex: 1;
      display: flex;
      align-items: center;
      padding: 8px 14px;
      gap: 16px;
      overflow-x: auto;
      font-size: 0.85rem;
    }

    .ticker-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      background: var(--rf-bg-canvas, #f8f9fa);
      border: 1px solid var(--rf-border-color, #121212);
      padding: 4px 8px;
    }

    .speaker-tag {
      font-weight: 800;
      color: var(--rf-color-blue, #1d3557);
    }
  `;

  @property({ type: String }) sessionId = 'session-live-1';
  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Array }) tokens: SpectatorToken[] = [];
  @property({ type: Object }) atmosphere: SpectatorAtmosphere | null = null;
  @property({ type: Array }) chronicle: SpectatorChronicleItem[] = [];
  @property({ type: Number }) round = 1;
  @property({ type: Boolean }) isLive = true;
  @property({ type: Boolean, attribute: 'transparent-mode', reflect: true }) transparentMode = false;

  private getTokenAt(x: number, y: number): SpectatorToken | undefined {
    return this.tokens.find((t) => t.x === x && t.y === y);
  }

  private getDefaultTokenColor(token: SpectatorToken): string {
    if (token.color) return token.color;
    if (token.isAiControlled) return 'var(--rf-color-yellow, #ffb703)';
    return 'var(--rf-color-blue, #1d3557)';
  }

  render() {
    return html`
      <!-- Top Broadcast Overlay Header -->
      <header class="stream-header">
        <div class="brand-group">
          ${this.isLive
            ? html`
                <span class="live-badge">
                  <span class="live-dot"></span>
                  SPECTATOR OVERLAY
                </span>
              `
            : html`<span class="live-badge" style="background:#4b5563">ARCHIVED</span>`}
          <span class="session-title">Runefoble Stream — Session ${this.sessionId}</span>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <span class="round-pill">ROUND ${this.round}</span>
          <span style="font-size:0.75rem; color:var(--rf-text-muted,#4b5563)">READ-ONLY BROADCAST</span>
        </div>
      </header>

      <!-- Active Scene Atmosphere Indicator -->
      ${this.atmosphere
        ? html`
            <section class="atmosphere-bar" aria-label="Scene Atmosphere">
              <span class="scene-tag">🏰 ${this.atmosphere.location_name}</span>
              <span class="scene-meta">Lighting: ${this.atmosphere.lighting}</span>
              <span class="scene-meta">| Mood: <strong>${this.atmosphere.mood}</strong></span>
              ${this.atmosphere.ambient_audio_prompt
                ? html`
                    <div class="audio-visualizer" title="Ambient Voice Narration Active">
                      <span class="audio-bar"></span>
                      <span class="audio-bar"></span>
                      <span class="audio-bar"></span>
                      <span class="audio-bar"></span>
                    </div>
                  `
                : ''}
            </section>
          `
        : ''}

      <!-- Read-Only Tactical Board -->
      <main class="board-container">
        <div
          class="grid"
          style="grid-template-columns: repeat(${this.cols}, 52px); grid-template-rows: repeat(${this.rows}, 52px);"
          role="grid"
          aria-label="Tactical Combat Grid (Spectator)"
        >
          ${Array.from({ length: this.rows }).map((_, y) =>
            Array.from({ length: this.cols }).map((_, x) => {
              const token = this.getTokenAt(x, y);
              return html`
                <div class="cell" data-x="${x}" data-y="${y}">
                  ${token
                    ? html`
                        <div
                          class="token ${token.isActiveTurn ? 'active-turn' : ''}"
                          style="background: ${this.getDefaultTokenColor(token)}; color: ${token.isAiControlled ? '#121212' : '#ffffff'};"
                          title="${token.name}"
                        >
                          <span>${token.name.slice(0, 2).toUpperCase()}</span>
                          <span class="token-label">${token.name}</span>
                          ${token.conditions && token.conditions.length > 0
                            ? html`<span class="token-condition" title="${token.conditions.join(', ')}">!</span>`
                            : ''}
                        </div>
                      `
                    : ''}
                </div>
              `;
            })
          )}
        </div>
      </main>

      <!-- Live Narrative Chronicle Ticker -->
      <footer class="chronicle-ticker" aria-label="Live Chronicle Feed">
        <div class="ticker-label">
          <span>🔮</span>
          <span>CHRONICLE</span>
        </div>
        <div class="ticker-stream">
          ${this.chronicle.length > 0
            ? this.chronicle.map(
                (item) => html`
                  <div class="ticker-item">
                    <span class="speaker-tag">${item.speaker}:</span>
                    <span>${item.text}</span>
                  </div>
                `
              )
            : html`<span style="color:var(--rf-text-muted,#4b5563)">Awaiting party actions...</span>`}
        </div>
      </footer>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-spectator-view': RunefobleSpectatorView;
  }
}
