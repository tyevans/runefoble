import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type {
  AoETemplateConfig,
  BoardToken,
  DragKinematicsState,
  GhostPreviewState,
  RadialActionType,
  TerrainCell,
} from './board-types.ts';
import {
  renderAoEBanner,
  renderAoEOverlay,
  renderBoardHeader,
  renderGhostBanner,
  renderRadialMenuOverlay,
  renderStatusBar,
} from './board-templates.ts';
import {
  cancelAoEPlacement,
  confirmAoEPlacement,
  executeRadialAction,
  handleBoardSocketMessage,
} from './board-actions.ts';
import { renderBoardGrid } from './board-grid.ts';
import { GhostPreviewEngine, parseIncomingGhostPreview } from './ghost_preview.ts';
import { computeDragUpdate, initDragState, isCellVisible, snapToGrid } from './kinematics.ts';
import { boardStyles } from './runefoble-board.styles.ts';
import './radial_menu.ts';
import './aoe_templates.ts';

export type * from './board-types.ts';
export * from './ghost_preview.ts';
export * from './kinematics.ts';
export * from './radial_menu.ts';
export * from './aoe_templates.ts';
export * from './board-actions.ts';

@customElement('runefoble-board')
export class RunefobleBoard extends LitElement {
  static styles = boardStyles;

  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Array }) tokens: BoardToken[] = [];
  @property({ type: Array }) terrainCells: TerrainCell[] = [];
  @property({ type: Object }) activeGhost: GhostPreviewState | null = null;
  @property({ type: Object }) activeAoE: AoETemplateConfig | null = null;
  @property({ type: String }) watcherStatus = 'Observing session...';
  @property({ type: Boolean }) fogOfWar = false;
  @property({ type: String }) activeTurnTokenId: string | null = null;
  @property({ type: String }) websocketUrl: string | null = null;

  @state() private selectedTokenId: string | null = null;
  @state() private radialTokenId: string | null = null;
  @state() private dragState: DragKinematicsState | null = null;
  @state() private localGhost: GhostPreviewState | null = null;
  @state() aoeAffectedTokenIds: string[] = [];
  @state() aoeAffectedCells: [number, number][] = [];

  ghostEngine: GhostPreviewEngine | null = null;
  ws: WebSocket | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.ghostEngine = new GhostPreviewEngine(
      (preview) => { this.localGhost = preview; this.requestUpdate(); },
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
    if (this.activeGhost) this.ghostEngine.stage(this.activeGhost);
    if (this.websocketUrl) this.connectWebSocket(this.websocketUrl);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.ghostEngine?.dispose();
    if (this.ws) { this.ws.close(); this.ws = null; }
  }

  updated(changedProperties: Map<string, any>) {
    if (changedProperties.has('activeGhost') && this.activeGhost !== this.localGhost) {
      if (this.activeGhost) this.ghostEngine?.stage(this.activeGhost);
      else this.ghostEngine?.cancel();
    }
  }

  private connectWebSocket(url: string) {
    try {
      this.ws = new WebSocket(url);
      this.ws.onmessage = (event) => {
        try { this.handleIncomingSocketMessage(JSON.parse(event.data)); } catch {}
      };
    } catch {}
  }

  public handleIncomingSocketMessage(data: any) {
    handleBoardSocketMessage(this, data);
  }

  public stageGhostPreview(data: any): GhostPreviewState | null {
    const parsed = parseIncomingGhostPreview(data, this.tokens, this.terrainCells);
    if (parsed) this.ghostEngine?.stage(parsed);
    return parsed;
  }

  public confirmGhostPreview(): GhostPreviewState | null {
    const ghost = this.ghostEngine?.confirm();
    if (ghost) {
      this.dispatchEvent(new CustomEvent('confirm-ghost', { detail: { ghost }, bubbles: true, composed: true }));
      this.dispatchEvent(new CustomEvent('move-token', { detail: { tokenId: ghost.tokenId, toX: ghost.toX, toY: ghost.toY }, bubbles: true, composed: true }));
    }
    return ghost ?? null;
  }

  public cancelGhostPreview(): void {
    const ghost = this.localGhost;
    this.ghostEngine?.cancel();
    if (ghost) this.dispatchEvent(new CustomEvent('cancel-ghost', { detail: { ghost }, bubbles: true, composed: true }));
  }

  public isCellRevealed(cellX: number, cellY: number): boolean {
    return isCellVisible(cellX, cellY, this.fogOfWar, this.tokens);
  }

  public openRadialMenu(tokenId: string) {
    this.radialTokenId = tokenId;
    this.selectedTokenId = tokenId;
  }

  public closeRadialMenu() {
    this.radialTokenId = null;
  }

  public handleRadialActionSelect(e: CustomEvent<{ action: RadialActionType; tokenId: string }>) {
    this.radialTokenId = null;
    executeRadialAction(this, e.detail.action, e.detail.tokenId);
  }

  public handleAoEChange(e: CustomEvent) {
    this.activeAoE = e.detail.config;
    this.aoeAffectedTokenIds = e.detail.affectedTokenIds;
    this.aoeAffectedCells = e.detail.affectedCells;
    this.requestUpdate();
  }

  public confirmAoETemplate() {
    confirmAoEPlacement(this);
  }

  public cancelAoETemplate() {
    cancelAoEPlacement(this);
  }

  private handleTokenPointerDown(e: PointerEvent, token: BoardToken) {
    if (e.button !== 0) return;
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    this.selectedTokenId = token.id;
    this.dragState = initDragState(token);
  }

  private handlePointerMove(e: PointerEvent) {
    if (!this.dragState?.isDragging) return;
    const gridEl = this.shadowRoot?.querySelector('.grid') as HTMLElement;
    if (!gridEl) return;
    const { cellX, cellY } = snapToGrid(e.clientX - gridEl.getBoundingClientRect().left, e.clientY - gridEl.getBoundingClientRect().top, 56, this.cols, this.rows);
    this.dragState = computeDragUpdate(this.dragState, cellX, cellY, this.terrainCells);
  }

  private handlePointerUp(e: PointerEvent) {
    if (!this.dragState?.isDragging) return;
    const { targetCellX: targetX, targetCellY: targetY, startX, startY, tokenId } = this.dragState;
    if (targetX !== startX || targetY !== startY) {
      this.dispatchEvent(new CustomEvent('move-token', { detail: { tokenId, toX: targetX, toY: targetY }, bubbles: true, composed: true }));
    } else {
      this.radialTokenId = tokenId;
    }
    try { (e.target as HTMLElement).releasePointerCapture(e.pointerId); } catch {}
    this.dragState = null;
  }

  private handleCellClick(x: number, y: number) {
    if (this.radialTokenId) { this.radialTokenId = null; return; }
    if (this.selectedTokenId && !this.dragState?.isDragging) {
      this.dispatchEvent(new CustomEvent('move-token', { detail: { tokenId: this.selectedTokenId, toX: x, toY: y }, bubbles: true, composed: true }));
      this.selectedTokenId = null;
    }
  }

  render() {
    const radialToken = this.radialTokenId ? this.tokens.find((t) => t.id === this.radialTokenId) ?? null : null;
    return html`
      ${renderBoardHeader(this.fogOfWar, () => { this.fogOfWar = !this.fogOfWar; }, this.watcherStatus)}
      ${renderBoardGrid({
        cols: this.cols,
        rows: this.rows,
        tokens: this.tokens,
        terrainCells: this.terrainCells,
        activeTurnTokenId: this.activeTurnTokenId,
        selectedTokenId: this.selectedTokenId,
        dragState: this.dragState,
        localGhost: this.localGhost,
        fogOfWar: this.fogOfWar,
        aoeAffectedTokens: this.aoeAffectedTokenIds,
        aoeAffectedCells: this.aoeAffectedCells,
        aoeOverlay: renderAoEOverlay(this.activeAoE, this.tokens, this.cols, this.rows, (e) => this.handleAoEChange(e)),
        radialMenu: renderRadialMenuOverlay(radialToken, (e) => this.handleRadialActionSelect(e), () => { this.radialTokenId = null; }),
        isCellRevealed: (x, y) => this.isCellRevealed(x, y),
        onCellClick: (x, y) => this.handleCellClick(x, y),
        onTokenPointerDown: (e, token) => this.handleTokenPointerDown(e, token),
        onPointerMove: (e) => this.handlePointerMove(e),
        onPointerUp: (e) => this.handlePointerUp(e),
        onGhostConfirm: () => this.confirmGhostPreview(),
      })}
      ${this.activeAoE
        ? renderAoEBanner(this.activeAoE, this.aoeAffectedTokenIds.length, () => this.confirmAoETemplate(), () => this.cancelAoETemplate())
        : renderGhostBanner(this.localGhost, () => this.confirmGhostPreview(), () => this.cancelGhostPreview())}
      ${renderStatusBar(this.selectedTokenId ? this.tokens.find((t) => t.id === this.selectedTokenId)?.name ?? null : null, this.cols, this.rows)}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-board': RunefobleBoard;
  }
}
