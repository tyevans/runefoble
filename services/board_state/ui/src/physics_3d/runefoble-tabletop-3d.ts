/**
 * Standalone Lit Web Component for 3D Miniature Tokens & WebGL Tabletop Physics.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, query } from 'lit/decorators.js';
import type { Miniature3DToken } from './miniature_mesh.ts';
import { TabletopPhysicsVisualizer } from './tabletop_canvas.ts';
import { PhysicsBridge } from './physics_bridge.ts';

@customElement('runefoble-tabletop-3d')
export class RunefobleTabletop3D extends LitElement {
  static styles = css`
    :host {
      display: block;
      position: relative;
      width: 100%;
      height: 100%;
      min-height: 440px;
      background: var(--rf-bg-surface, #0f172a);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #1e293b);
      box-sizing: border-box;
      overflow: hidden;
    }
    canvas {
      display: block;
      width: 100%;
      height: 100%;
    }
    .hud-controls {
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      gap: 6px;
      z-index: 20;
    }
    .hud-btn {
      background: var(--rf-bg-canvas, #1e293b);
      color: var(--rf-text-primary, #f8fafc);
      border: 1px solid var(--rf-border-color, #334155);
      padding: 4px 10px;
      font-size: 0.75rem;
      font-weight: 700;
      border-radius: 4px;
      cursor: pointer;
    }
  `;

  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Array }) tokens: Miniature3DToken[] = [];
  @property({ type: Array }) terrainCells: Array<{ x: number; y: number; elevation?: number }> = [];
  @property({ type: String }) theme: 'dark' | 'light' | 'high-contrast' = 'dark';
  @property({ type: String }) boardId: string | null = null;

  @query('canvas') private canvasElement!: HTMLCanvasElement;
  public visualizer: TabletopPhysicsVisualizer | null = null;
  public bridge: PhysicsBridge | null = null;

  firstUpdated() {
    if (this.canvasElement) {
      this.canvasElement.width = this.canvasElement.clientWidth || this.cols * 54;
      this.canvasElement.height = this.canvasElement.clientHeight || this.rows * 54;
      this.visualizer = new TabletopPhysicsVisualizer(this.canvasElement, {
        cols: this.cols, rows: this.rows, theme: this.theme,
      });
      this.visualizer.updateTokens(this.tokens);
      this.visualizer.updateTerrain(this.terrainCells);
      this.bridge = new PhysicsBridge(this, this.visualizer);
    }
  }

  updated(changedProps: Map<string, any>) {
    if (changedProps.has('tokens') && this.visualizer) this.visualizer.updateTokens(this.tokens);
    if (changedProps.has('terrainCells') && this.visualizer) this.visualizer.updateTerrain(this.terrainCells);
    if (changedProps.has('theme') && this.visualizer) this.visualizer.setTheme(this.theme);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.visualizer?.dispose();
    this.visualizer = null;
    this.bridge = null;
  }

  public rollDice(dice: any) { this.visualizer?.rollDice(dice); }
  public knockbackToken(kb: any) { this.visualizer?.knockbackToken(kb); }
  public handleWebSocketMessage(data: any): boolean { return this.bridge?.handleWebSocketMessage(data) ?? false; }

  render() {
    return html`
      <canvas></canvas>
      <div class="hud-controls">
        <button class="hud-btn" @click=${() => this.rollDice({ faceValue: 20, settledCell: [3, 3] })}>🎲 Roll d20</button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-tabletop-3d': RunefobleTabletop3D;
  }
}
