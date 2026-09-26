import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { spectatorViewStyles } from './runefoble-spectator-view.styles.ts';

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
  static styles = [spectatorViewStyles];

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
    if (token.isAiControlled) return 'var(--rf-color-yellow)';
    return 'var(--rf-color-blue)';
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
            : html`<span class="live-badge" style="background:var(--rf-text-muted)">ARCHIVED</span>`}
          <span class="session-title">Runefoble Stream — Session ${this.sessionId}</span>
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
          <span class="round-pill">ROUND ${this.round}</span>
          <span style="font-size:0.75rem; color:var(--rf-text-muted)">READ-ONLY BROADCAST</span>
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
                          style="background: ${this.getDefaultTokenColor(token)}; color: ${token.isAiControlled ? 'var(--rf-color-dark)' : 'var(--rf-text-inverse)'};"
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
            : html`<span style="color:var(--rf-text-muted)">Awaiting party actions...</span>`}
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
