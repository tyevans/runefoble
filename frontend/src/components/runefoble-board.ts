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
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
      transition: background 0.15s ease-in-out;
    }
    .cell:hover {
      background: #1e293b;
    }
    .token {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 0.8rem;
      color: #ffffff;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
      user-select: none;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .token:hover {
      transform: scale(1.1);
    }
    .token.ai {
      border: 2px dashed #ec4899;
    }
    .status-bar {
      margin-top: 12px;
      font-size: 0.85rem;
      color: #94a3b8;
      display: flex;
      justify-content: space-between;
    }
  `;

  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Array }) tokens: BoardToken[] = [];
  @property({ type: String }) watcherStatus = 'Observing session...';

  @state() private selectedTokenId: string | null = null;

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

  render() {
    const gridStyle = `grid-template-columns: repeat(${this.cols}, 54px); grid-template-rows: repeat(${this.rows}, 54px);`;

    return html`
      <div class="header">
        <div class="title">
          <span>⚔️ Tactical Realm</span>
        </div>
        <div class="watcher-badge">
          <span>👁️ The Watcher:</span>
          <span>${this.watcherStatus}</span>
        </div>
      </div>

      <div class="grid" style="${gridStyle}">
        ${Array.from({ length: this.rows * this.cols }).map((_, index) => {
          const x = index % this.cols;
          const y = Math.floor(index / this.cols);
          const token = this.tokens.find((t) => t.x === x && t.y === y);

          return html`
            <div class="cell" @click="${() => this.handleCellClick(x, y)}">
              ${token
                ? html`
                    <div
                      class="token ${token.isAiControlled ? 'ai' : ''}"
                      style="background: ${token.color || '#3b82f6'}; ${this.selectedTokenId === token.id ? 'outline: 3px solid #facc15;' : ''}"
                      @click="${(e: MouseEvent) => this.handleTokenClick(e, token)}"
                      title="${token.name}${token.isAiControlled ? ' (AI Stand-in)' : ''}"
                    >
                      ${token.name.slice(0, 2).toUpperCase()}
                    </div>
                  `
                : ''}
            </div>
          `;
        })}
      </div>

      <div class="status-bar">
        <span>Selected: ${this.selectedTokenId ? this.tokens.find(t => t.id === this.selectedTokenId)?.name : 'None'}</span>
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
