import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface BoardToken {
  id: string;
  name: string;
  x: number;
  y: number;
  avatarUrl?: string;
  isAiControlled?: boolean;
  color?: string;
  hp?: number;
  maxHp?: number;
  visionRadius?: number;
  isHostile?: boolean;
  isActiveTurn?: boolean;
}

@customElement('runefoble-board')
export class RunefobleBoard extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary, #121212);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      padding: 16px;
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      box-sizing: border-box;
      transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      flex-wrap: wrap;
      gap: 12px;
    }
    .title {
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--rf-text-primary, #121212);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .watcher-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--rf-bg-canvas, #f8f9fa);
      color: var(--rf-text-primary, #121212);
      padding: 4px 10px;
      border-radius: var(--rf-border-radius, 0px);
      font-size: 0.75rem;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-weight: 700;
    }
    .fog-toggle {
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-muted, #4b5563);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      padding: 4px 8px;
      font-size: 0.75rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      transition: all 0.2s;
    }
    .fog-toggle.active {
      background: var(--rf-accent-tertiary, #ffb703);
      color: var(--rf-color-dark, #121212);
    }
    .grid {
      display: grid;
      gap: 2px;
      background: var(--rf-border-color, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      overflow: hidden;
      width: fit-content;
      margin: 0 auto;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }
    .cell {
      width: 54px;
      height: 54px;
      background: var(--rf-bg-surface, #ffffff);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      transition: background 0.15s ease-in-out, filter 0.2s ease-in-out;
    }
    .cell:hover:not(.fog) {
      background: var(--rf-bg-canvas, #f8f9fa);
    }
    .cell.fog {
      background: var(--rf-color-dark, #121212);
      filter: brightness(0.6);
      cursor: not-allowed;
    }
    .cell.fog::after {
      content: '';
      position: absolute;
      inset: 0;
      background: repeating-linear-gradient(
        45deg,
        rgba(0, 0, 0, 0.4),
        rgba(0, 0, 0, 0.4) 4px,
        rgba(0, 0, 0, 0.6) 4px,
        rgba(0, 0, 0, 0.6) 8px
      );
      pointer-events: none;
    }
    .coord-label {
      position: absolute;
      top: 2px;
      left: 2px;
      font-size: 0.6rem;
      color: var(--rf-text-muted, #4b5563);
      pointer-events: none;
      user-select: none;
      font-weight: 700;
    }
    .token-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      z-index: 2;
    }
    .token {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.75rem;
      color: #ffffff;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      user-select: none;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
      position: relative;
    }
    .token:hover {
      transform: scale(1.12);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }
    .token.ai {
      outline: 2px dashed var(--rf-accent-tertiary, #ffb703);
      outline-offset: 1px;
    }
    .token.hostile {
      outline: 2px solid var(--rf-accent-primary, #e63946);
      outline-offset: 1px;
    }
    .token.active-turn {
      animation: gold-pulse 1.6s infinite ease-in-out;
      outline: 3px solid var(--rf-accent-tertiary, #ffb703);
    }
    @keyframes gold-pulse {
      0% {
        box-shadow: 0 0 0 0 rgba(255, 183, 3, 0.8), var(--rf-shadow-sm, 2px 2px 0px #121212);
      }
      70% {
        box-shadow: 0 0 0 8px rgba(255, 183, 3, 0), var(--rf-shadow-sm, 2px 2px 0px #121212);
      }
      100% {
        box-shadow: 0 0 0 0 rgba(255, 183, 3, 0), var(--rf-shadow-sm, 2px 2px 0px #121212);
      }
    }
    .health-bar-container {
      width: 36px;
      height: 6px;
      background: var(--rf-bg-canvas, #f8f9fa);
      border: 1px solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      margin-top: 2px;
      overflow: hidden;
    }
    .health-bar-fill {
      height: 100%;
      transition: width 0.3s ease-in-out, background 0.3s ease-in-out;
    }
    .status-bar {
      margin-top: 12px;
      font-size: 0.85rem;
      color: var(--rf-text-muted, #4b5563);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }
    .legend {
      display: flex;
      gap: 12px;
      font-size: 0.75rem;
      color: var(--rf-text-muted, #4b5563);
      flex-wrap: wrap;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      border: 1px solid var(--rf-border-color, #121212);
    }
  `;

  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Array }) tokens: BoardToken[] = [];
  @property({ type: String }) watcherStatus = 'Observing session...';
  @property({ type: Boolean }) fogOfWar = false;
  @property({ type: String }) activeTurnTokenId: string | null = null;

  @state() private selectedTokenId: string | null = null;

  private isCellRevealed(cellX: number, cellY: number): boolean {
    if (!this.fogOfWar) {
      return true;
    }
    const friendlyTokens = this.tokens.filter((t) => !t.isHostile);
    if (friendlyTokens.length === 0) {
      return true;
    }
    return friendlyTokens.some((token) => {
      const radius = token.visionRadius ?? 2;
      const dx = Math.abs(token.x - cellX);
      const dy = Math.abs(token.y - cellY);
      return Math.max(dx, dy) <= radius;
    });
  }

  private handleCellClick(x: number, y: number) {
    if (this.selectedTokenId) {
      this.dispatchEvent(
        new CustomEvent('move-token', {
          detail: { tokenId: this.selectedTokenId, toX: x, toY: y },
          bubbles: true,
          composed: true,
        })
      );
      this.selectedTokenId = null;
    }
  }

  private handleTokenClick(e: MouseEvent, token: BoardToken) {
    e.stopPropagation();
    this.selectedTokenId = this.selectedTokenId === token.id ? null : token.id;
    this.dispatchEvent(
      new CustomEvent('select-token', {
        detail: { token },
        bubbles: true,
        composed: true,
      })
    );
  }

  private toggleFog() {
    this.fogOfWar = !this.fogOfWar;
  }

  private getHealthBarColor(hp: number, maxHp: number): string {
    const ratio = Math.max(0, Math.min(1, hp / maxHp));
    if (ratio > 0.5) return 'var(--rf-accent-secondary, #1d3557)';
    if (ratio > 0.2) return 'var(--rf-accent-tertiary, #ffb703)';
    return 'var(--rf-accent-primary, #e63946)';
  }

  render() {
    const gridStyle = `grid-template-columns: repeat(${this.cols}, 54px); grid-template-rows: repeat(${this.rows}, 54px);`;

    return html`
      <div class="header">
        <div class="title">
          <span>⚔️ Tactical Realm</span>
        </div>
        <div class="controls">
          <button
            class="fog-toggle ${this.fogOfWar ? 'active' : ''}"
            @click="${this.toggleFog}"
            title="Toggle Fog of War visibility"
          >
            🌫️ Fog of War: ${this.fogOfWar ? 'ON' : 'OFF'}
          </button>
          <div class="watcher-badge">
            <span>👁️ The Watcher:</span>
            <span>${this.watcherStatus}</span>
          </div>
        </div>
      </div>

      <div class="grid" style="${gridStyle}">
        ${Array.from({ length: this.rows * this.cols }).map((_, index) => {
          const x = index % this.cols;
          const y = Math.floor(index / this.cols);
          const isRevealed = this.isCellRevealed(x, y);
          const token = this.tokens.find((t) => t.x === x && t.y === y);
          const isHiddenHostile = token?.isHostile && !isRevealed;
          const isActiveTurn =
            token && (token.isActiveTurn || token.id === this.activeTurnTokenId);

          return html`
            <div
              class="cell ${!isRevealed ? 'fog' : ''}"
              @click="${() => isRevealed && this.handleCellClick(x, y)}"
            >
              <span class="coord-label">${x},${y}</span>
              ${token && !isHiddenHostile
                ? html`
                    <div class="token-container">
                      <div
                        class="token ${token.isAiControlled ? 'ai' : ''} ${token.isHostile ? 'hostile' : ''} ${isActiveTurn ? 'active-turn' : ''}"
                        style="background: ${token.color || 'var(--rf-accent-secondary, #1d3557)'}; ${this.selectedTokenId === token.id ? 'outline: 3px solid var(--rf-accent-primary, #e63946);' : ''}"
                        @click="${(e: MouseEvent) => this.handleTokenClick(e, token)}"
                        title="${token.name}${token.isAiControlled ? ' (AI Stand-in)' : ''}${token.hp !== undefined ? ` [${token.hp}/${token.maxHp ?? token.hp} HP]` : ''}${isActiveTurn ? ' (Active Turn)' : ''}"
                      >
                        ${token.name.slice(0, 2).toUpperCase()}
                      </div>
                      ${token.hp !== undefined && token.maxHp !== undefined
                        ? html`
                            <div class="health-bar-container">
                              <div
                                class="health-bar-fill"
                                style="width: ${Math.max(0, Math.min(100, (token.hp / token.maxHp) * 100))}%; background: ${this.getHealthBarColor(token.hp, token.maxHp)};"
                              ></div>
                            </div>
                          `
                        : ''}
                    </div>
                  `
                : ''}
            </div>
          `;
        })}
      </div>

      <div class="status-bar">
        <span>Selected: ${this.selectedTokenId ? this.tokens.find((t) => t.id === this.selectedTokenId)?.name : 'None'}</span>
        <div class="legend">
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-tertiary, #ffb703)"></span> Turn</span>
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-primary, #e63946)"></span> AI</span>
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-secondary, #1d3557)"></span> Player</span>
        </div>
        <span>Grid: ${this.cols} x ${this.rows}</span>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-board': RunefobleBoard;
  }
}
