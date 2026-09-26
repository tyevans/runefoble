import { LitElement, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type {
  BoardToken,
  DragKinematicsState,
  GhostPreviewState,
  TerrainCell,
} from './board-types.ts';
import {
  getHealthBarColor,
  renderDistanceRuler,
  renderGhostBanner,
  renderVectorOverlay,
} from './board-templates.ts';
import {
  calculateVectorLineCoordinates,
  GhostPreviewEngine,
  parseIncomingGhostPreview,
} from './ghost_preview.ts';
import {
  computeGridTrajectory,
  computeRouteMetrics,
  snapToGrid,
} from './kinematics.ts';
import { boardStyles } from './runefoble-board.styles.ts';

export type * from './board-types.ts';
export * from './ghost_preview.ts';
export * from './kinematics.ts';

@customElement('runefoble-board')
export class RunefobleBoard extends LitElement {
  static styles = boardStyles;

  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Array }) tokens: BoardToken[] = [];
  @property({ type: Array }) terrainCells: TerrainCell[] = [];
  @property({ type: Object }) activeGhost: GhostPreviewState | null = null;
  @property({ type: String }) watcherStatus = 'Observing session...';
  @property({ type: Boolean }) fogOfWar = false;
  @property({ type: String }) activeTurnTokenId: string | null = null;
  @property({ type: String }) websocketUrl: string | null = null;

  @state() private selectedTokenId: string | null = null;
  @state() private dragState: DragKinematicsState | null = null;
  @state() private localGhost: GhostPreviewState | null = null;

  private ghostEngine: GhostPreviewEngine | null = null;
  private ws: WebSocket | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.ghostEngine = new GhostPreviewEngine(
      (preview) => {
        this.localGhost = preview;
        this.requestUpdate();
      },
      () => {
        this.dispatchEvent(
          new CustomEvent('ghost-timeout', {
            detail: { tokenId: this.localGhost?.tokenId },
            bubbles: true,
            composed: true,
          })
        );
      }
    );

    if (this.activeGhost) {
      this.ghostEngine.stage(this.activeGhost);
    }
    if (this.websocketUrl) {
      this.connectWebSocket(this.websocketUrl);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.ghostEngine?.dispose();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  updated(changedProperties: Map<string, any>) {
    if (changedProperties.has('activeGhost') && this.activeGhost !== this.localGhost) {
      if (this.activeGhost) {
        this.ghostEngine?.stage(this.activeGhost);
      } else {
        this.ghostEngine?.cancel();
      }
    }
  }

  private connectWebSocket(url: string) {
    try {
      this.ws = new WebSocket(url);
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingSocketMessage(data);
        } catch {
          // ignore non-json messages
        }
      };
    } catch {
      // ignore connection failure in disconnected dev modes
    }
  }

  public handleIncomingSocketMessage(data: any) {
    const action = data.action || data.type;
    if (action === 'ghost_preview' || action === 'preview_move' || action === 'SpeechIntentParsed') {
      const parsed = parseIncomingGhostPreview(data, this.tokens, this.terrainCells);
      if (parsed) {
        this.ghostEngine?.stage(parsed);
      }
    } else if (action === 'token_moved' || action === 'preview_cancelled') {
      this.ghostEngine?.cancel();
    }
  }

  public stageGhostPreview(data: any): GhostPreviewState | null {
    const parsed = parseIncomingGhostPreview(data, this.tokens, this.terrainCells);
    if (parsed) {
      this.ghostEngine?.stage(parsed);
    }
    return parsed;
  }

  public confirmGhostPreview(): GhostPreviewState | null {
    const ghost = this.ghostEngine?.confirm();
    if (ghost) {
      this.dispatchEvent(
        new CustomEvent('confirm-ghost', {
          detail: { ghost },
          bubbles: true,
          composed: true,
        })
      );
      this.dispatchEvent(
        new CustomEvent('move-token', {
          detail: { tokenId: ghost.tokenId, toX: ghost.toX, toY: ghost.toY },
          bubbles: true,
          composed: true,
        })
      );
    }
    return ghost ?? null;
  }

  public cancelGhostPreview(): void {
    const ghost = this.localGhost;
    this.ghostEngine?.cancel();
    if (ghost) {
      this.dispatchEvent(
        new CustomEvent('cancel-ghost', {
          detail: { ghost },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  private isCellRevealed(cellX: number, cellY: number): boolean {
    if (!this.fogOfWar) return true;
    const friendlyTokens = this.tokens.filter((t) => !t.isHostile);
    if (friendlyTokens.length === 0) return true;
    return friendlyTokens.some((token) => {
      const radius = token.visionRadius ?? 2;
      const dx = Math.abs(token.x - cellX);
      const dy = Math.abs(token.y - cellY);
      return Math.max(dx, dy) <= radius;
    });
  }

  private handleTokenPointerDown(e: PointerEvent, token: BoardToken) {
    if (e.button !== 0) return;
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    this.selectedTokenId = token.id;
    this.dragState = {
      tokenId: token.id,
      startX: token.x,
      startY: token.y,
      currentX: token.x,
      currentY: token.y,
      targetCellX: token.x,
      targetCellY: token.y,
      isDragging: true,
      totalDistanceFt: 0,
      waypoints: [],
      difficultCells: [],
      hazardCells: [],
    };
  }

  private handlePointerMove(e: PointerEvent) {
    if (!this.dragState?.isDragging) return;

    const gridEl = this.shadowRoot?.querySelector('.grid') as HTMLElement;
    if (!gridEl) return;

    const rect = gridEl.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    const { cellX, cellY } = snapToGrid(offsetX, offsetY, 56, this.cols, this.rows);

    if (cellX !== this.dragState.targetCellX || cellY !== this.dragState.targetCellY) {
      const path = computeGridTrajectory(
        this.dragState.startX,
        this.dragState.startY,
        cellX,
        cellY
      );
      const metrics = computeRouteMetrics(path, this.terrainCells);

      this.dragState = {
        ...this.dragState,
        targetCellX: cellX,
        targetCellY: cellY,
        totalDistanceFt: metrics.totalDistanceFt,
        waypoints: metrics.waypoints,
        difficultCells: metrics.difficultCells,
        hazardCells: metrics.hazardCells,
      };
    }
  }

  private handlePointerUp(e: PointerEvent) {
    if (!this.dragState?.isDragging) return;

    const targetX = this.dragState.targetCellX;
    const targetY = this.dragState.targetCellY;
    const tokenId = this.dragState.tokenId;

    if (targetX !== this.dragState.startX || targetY !== this.dragState.startY) {
      this.dispatchEvent(
        new CustomEvent('move-token', {
          detail: { tokenId, toX: targetX, toY: targetY },
          bubbles: true,
          composed: true,
        })
      );
    }

    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    this.dragState = null;
  }

  private handleCellClick(x: number, y: number) {
    if (this.selectedTokenId && !this.dragState?.isDragging) {
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

  private toggleFog() {
    this.fogOfWar = !this.fogOfWar;
  }

  render() {
    const gridStyle = `grid-template-columns: repeat(${this.cols}, 54px); grid-template-rows: repeat(${this.rows}, 54px);`;
    const ghost = this.localGhost;

    let ghostVector: ReturnType<typeof calculateVectorLineCoordinates> | null = null;
    if (ghost && (ghost.fromX !== ghost.toX || ghost.fromY !== ghost.toY)) {
      ghostVector = calculateVectorLineCoordinates(ghost.fromX, ghost.fromY, ghost.toX, ghost.toY, 56);
    }

    const activeWaypoints = this.dragState?.isDragging
      ? this.dragState.waypoints
      : (ghost?.waypoints || []);

    const waypointSet = new Set(activeWaypoints.map((w) => `${w.x},${w.y}`));

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

      <div class="grid-wrapper">
        <div
          class="grid"
          style="${gridStyle}"
          @pointermove="${this.handlePointerMove}"
          @pointerup="${this.handlePointerUp}"
        >
          ${renderVectorOverlay(ghostVector)}

          ${Array.from({ length: this.rows * this.cols }).map((_, index) => {
            const x = index % this.cols;
            const y = Math.floor(index / this.cols);
            const isRevealed = this.isCellRevealed(x, y);
            const terrain = this.terrainCells.find((c) => c.x === x && c.y === y);
            const isDifficult = terrain?.terrainType === 'difficult';
            const hazardName = terrain?.hazard;
            const isWaypoint = waypointSet.has(`${x},${y}`);

            const token = this.tokens.find((t) => t.x === x && t.y === y);
            const isHiddenHostile = token?.isHostile && !isRevealed;
            const isActiveTurn = token && (token.isActiveTurn || token.id === this.activeTurnTokenId);
            const isGhostCell = ghost && ghost.toX === x && ghost.toY === y;
            const ghostToken = ghost ? this.tokens.find((t) => t.id === ghost.tokenId) : null;

            return html`
              <div
                class="cell ${!isRevealed ? 'fog' : ''} ${isDifficult ? 'difficult-terrain' : ''} ${hazardName ? 'hazard-cell' : ''} ${isWaypoint ? 'waypoint-path' : ''}"
                @click="${() => isRevealed && this.handleCellClick(x, y)}"
              >
                <span class="coord-label">${x},${y}</span>

                ${isDifficult ? html`<span class="terrain-badge difficult" title="Difficult terrain: +5ft">▲ +5ft</span>` : nothing}
                ${hazardName ? html`<span class="terrain-badge hazard" title="Hazard: ${hazardName}">⚠️ ${hazardName}</span>` : nothing}

                ${token && !isHiddenHostile
                  ? html`
                      <div class="token-container">
                        <div
                          class="token ${token.isAiControlled ? 'ai' : ''} ${token.isHostile ? 'hostile' : ''} ${isActiveTurn ? 'active-turn' : ''} ${this.dragState?.tokenId === token.id ? 'dragging' : ''}"
                          style="background: ${token.color || 'var(--rf-accent-secondary)'}; ${this.selectedTokenId === token.id ? 'outline: 3px solid var(--rf-accent-primary);' : ''}"
                          @pointerdown="${(e: PointerEvent) => this.handleTokenPointerDown(e, token)}"
                          title="${token.name}${token.isAiControlled ? ' (AI Stand-in)' : ''}${token.hp !== undefined ? ` [${token.hp}/${token.maxHp ?? token.hp} HP]` : ''}${isActiveTurn ? ' (Active Turn)' : ''}"
                        >
                          ${token.name.slice(0, 2).toUpperCase()}
                        </div>
                        ${token.hp !== undefined && token.maxHp !== undefined
                          ? html`
                              <div class="health-bar-container">
                                <div
                                  class="health-bar-fill"
                                  style="width: ${Math.max(0, Math.min(100, (token.hp / token.maxHp) * 100))}%; background: ${getHealthBarColor(token.hp, token.maxHp)};"
                                ></div>
                              </div>
                            `
                          : nothing}
                      </div>
                    `
                  : nothing}

                ${isGhostCell
                  ? html`
                      <div
                        class="ghost-token"
                        style="background: ${ghostToken?.color || 'var(--rf-accent-secondary)'};"
                        @click="${() => this.confirmGhostPreview()}"
                        title="Click to confirm move for ${ghost?.tokenName || 'token'}"
                      >
                        ${(ghost?.tokenName || ghostToken?.name || 'GH').slice(0, 2).toUpperCase()}
                      </div>
                    `
                  : nothing}
              </div>
            `;
          })}
        </div>

        ${renderDistanceRuler(this.dragState)}
      </div>

      ${renderGhostBanner(
        ghost,
        () => this.confirmGhostPreview(),
        () => this.cancelGhostPreview()
      )}

      <div class="status-bar">
        <span>Selected: ${this.selectedTokenId ? this.tokens.find((t) => t.id === this.selectedTokenId)?.name : 'None'}</span>
        <div class="legend">
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-tertiary)"></span> Turn</span>
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-primary)"></span> AI</span>
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-secondary)"></span> Player</span>
          <span class="legend-item"><span class="dot" style="background: repeating-linear-gradient(45deg, var(--rf-accent-tertiary), var(--rf-accent-tertiary) 2px, var(--rf-bg-surface) 2px, var(--rf-bg-surface) 4px)"></span> Difficult</span>
          <span class="legend-item"><span class="dot" style="background: var(--rf-accent-primary)"></span> Hazard</span>
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
