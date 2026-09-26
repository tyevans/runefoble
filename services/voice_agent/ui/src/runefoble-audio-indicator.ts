import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('runefoble-audio-indicator')
export class RunefobleAudioIndicator extends LitElement {
  @property({ type: String }) peerName = 'Adventurer';
  @property({ type: String }) role: 'player' | 'dungeon_master' | 'spectator' = 'player';
  @property({ type: Number }) audioLevel = 0.0; // 0.0 to 1.0
  @property({ type: Boolean }) isSpeaking = false;
  @property({ type: Boolean }) isMuted = false;
  @property({ type: Array }) activeFilters: string[] = [];

  static styles = css`
    :host {
      display: inline-block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary);
    }
    .indicator-card {
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm);
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
      min-width: 220px;
      box-sizing: border-box;
    }
    .indicator-card.speaking {
      border-color: var(--rf-accent-tertiary);
      box-shadow: var(--rf-shadow);
    }
    .avatar-badge {
      width: 36px;
      height: 36px;
      background: var(--rf-bg-canvas);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: 0.9rem;
      position: relative;
    }
    .avatar-badge.speaking {
      background: var(--rf-accent-tertiary);
      animation: pulse 1.2s infinite ease-in-out;
    }
    .avatar-badge.muted {
      opacity: 0.6;
    }
    .mute-icon {
      position: absolute;
      bottom: -4px;
      right: -4px;
      font-size: 0.75rem;
      background: var(--rf-bg-surface);
      border-radius: 50%;
      line-height: 1;
    }
    .peer-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .peer-header {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .peer-name {
      font-weight: 700;
      font-size: 0.9rem;
      color: var(--rf-text-primary);
    }
    .role-tag {
      font-size: 0.65rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 1px 5px;
      border: 1px solid var(--rf-border-color);
      background: var(--rf-bg-canvas);
    }
    .role-tag.dm {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
    }
    .meter-container {
      width: 100%;
      height: 6px;
      background: var(--rf-bg-inset, var(--rf-bg-canvas));
      border: 1px solid var(--rf-border-color);
      margin-top: 4px;
      overflow: hidden;
    }
    .meter-fill {
      height: 100%;
      background: var(--rf-accent-secondary);
      transition: width 0.1s ease;
    }
    .meter-fill.hot {
      background: var(--rf-accent-primary);
    }
    .filters-row {
      display: flex;
      gap: 4px;
      margin-top: 4px;
      flex-wrap: wrap;
    }
    .filter-badge {
      font-size: 0.65rem;
      background: var(--rf-bg-surface);
      border: 1px dashed var(--rf-border-subtle, var(--rf-border-color));
      padding: 0 4px;
      color: var(--rf-text-muted);
    }
    @keyframes pulse {
      0% {
        box-shadow: 0 0 0 0 rgba(255, 183, 3, 0.7);
      }
      70% {
        box-shadow: 0 0 0 8px rgba(255, 183, 3, 0);
      }
      100% {
        box-shadow: 0 0 0 0 rgba(255, 183, 3, 0);
      }
    }
  `;

  render() {
    const clampedLevel = Math.max(0, Math.min(1, this.audioLevel));
    const widthPct = Math.round(clampedLevel * 100);
    const isHot = clampedLevel > 0.75;
    const initial = this.peerName.charAt(0).toUpperCase();

    return html`
      <div class="indicator-card ${this.isSpeaking && !this.isMuted ? 'speaking' : ''}">
        <div class="avatar-badge ${this.isSpeaking && !this.isMuted ? 'speaking' : ''} ${this.isMuted ? 'muted' : ''}">
          ${initial}
          ${this.isMuted ? html`<span class="mute-icon" title="Muted">🔇</span>` : ''}
        </div>
        <div class="peer-info">
          <div class="peer-header">
            <span class="peer-name">${this.peerName}</span>
            <span class="role-tag ${this.role === 'dungeon_master' ? 'dm' : ''}">
              ${this.role === 'dungeon_master' ? 'DM' : this.role}
            </span>
          </div>
          <div class="meter-container" aria-label="Audio level meter">
            <div
              class="meter-fill ${isHot ? 'hot' : ''}"
              style="width: ${this.isMuted ? 0 : widthPct}%;"
            ></div>
          </div>
          ${this.activeFilters.length > 0
            ? html`
                <div class="filters-row">
                  ${this.activeFilters.map((f) => html`<span class="filter-badge">✨ ${f}</span>`)}
                </div>
              `
            : ''}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-audio-indicator': RunefobleAudioIndicator;
  }
}
