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
      font-family: system-ui, -apple-system, sans-serif;
      color: #e2e8f0;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #1e293b;
    }
    .title {
      font-size: 1.25rem;
      font-weight: 700;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .watcher-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #1e1b4b;
      color: #a78bfa;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 0.75rem;
      border: 1px solid #4338ca;
    }
    .fog-toggle {
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 0.75rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s;
    }
    .fog-toggle.active {
      background: #0284c7;
      color: #ffffff;
      border-color: #38bdf8;
    }
    .grid {
      display: grid;
      gap: 2px;
      background: #1e293b;
      border: 2px solid #475569;
      border-radius: 8px;
      overflow: hidden;
      width: fit-content;
      margin: 0 auto;
    }
    .cell {
      width: 54px;
      height: 54px;
      background: #0f172a;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      transition: background 0.15s ease-in-out, filter 0.2s ease-in-out;
    }
    .cell:hover:not(.fog) {
      background: #1e293b;
    }
    .cell.fog {
      background: #050811;
      filter: brightness(0.35);
      cursor: not-allowed;
    }
    .cell.fog::after {
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(circle, rgba(15, 23, 42, 0.4) 0%, rgba(2, 6, 23, 0.95) 100%);
      pointer-events: none;
    }
    .coord-label {
      position: absolute;
      top: 2px;
      left: 2px;
      font-size: 0.6rem;
      color: #475569;
      pointer-events: none;
      user-select: none;
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
      font-weight: bold;
      font-size: 0.75rem;
      color: #ffffff;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
      user-select: none;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
      position: relative;
    }
    .token:hover {
      transform: scale(1.12);
    }
    .token.ai {
      border: 2px dashed #ec4899;
    }
    .token.hostile {
      border: 2px solid #ef4444;
    }
    .token.active-turn {
      animation: gold-pulse 1.6s infinite ease-in-out;
      outline: 3px solid #facc15;
    }
    @keyframes gold-pulse {
      0% {
        box-shadow: 0 0 0 0 rgba(250, 204, 21, 0.8), 0 4px 6px rgba(0, 0, 0, 0.4);
      }
      70% {
        box-shadow: 0 0 0 8px rgba(250, 204, 21, 0), 0 4px 6px rgba(0, 0, 0, 0.4);
      }
      100% {
        box-shadow: 0 0 0 0 rgba(250, 204, 21, 0), 0 4px 6px rgba(0, 0, 0, 0.4);
      }
    }
    .health-bar-container {
      width: 36px;
      height: 4px;
      background: #334155;
      border-radius: 2px;
      margin-top: 2px;
      overflow: hidden;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    .health-bar-fill {
      height: 100%;
      transition: width 0.3s ease-in-out, background 0.3s ease-in-out;
    }
    .status-bar {
      margin-top: 12px;
      font-size: 0.85rem;
      color: #94a3b8;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .legend {
      display: flex;
      gap: 12px;
      font-size: 0.75rem;
      color: #64748b;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
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
    // Check if any friendly (non-hostile) token can see this cell
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
    if (ratio > 0.5) return '#22c55e'; // Green
    if (ratio > 0.2) return '#eab308'; // Yellow
    return '#ef4444'; // Red
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
                        style="background: ${token.color || '#3b82f6'}; ${this.selectedTokenId === token.id ? 'outline: 3px solid #38bdf8;' : ''}"
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
          <span class="legend-item"><span class="dot" style="background: #facc15"></span> Turn Glow</span>
          <span class="legend-item"><span class="dot" style="background: #ec4899"></span> AI Stand-in</span>
          <span class="legend-item"><span class="dot" style="background: #22c55e"></span> HP Bar</span>
          <span class="legend-item"><span class="dot" style="background: #0284c7"></span> Player</span>
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
