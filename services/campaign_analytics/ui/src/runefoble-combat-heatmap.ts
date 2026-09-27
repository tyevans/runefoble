/**
 * Lit Web Component: <runefoble-combat-heatmap>
 * Governed by ADR-0004, ADR-0007, ADR-0011, and ADR-0013.
 */

import { LitElement, html, type PropertyValues } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { combatHeatmapStyles } from './runefoble-combat-heatmap.styles.ts';
import type {
  CampaignHeatmapResponse,
  HeatmapCell,
  HazardHotspot,
  KnockoutLocation,
  MovementCorridor,
} from './types.ts';

@customElement('runefoble-combat-heatmap')
export class RunefobleCombatHeatmap extends LitElement {
  static styles = [combatHeatmapStyles];

  @property({ type: Object }) heatmapData: CampaignHeatmapResponse | null = null;
  @property({ type: Number }) gridSize = 10;
  @property({ type: Number }) cellPixelSize = 36;
  @property({ type: String }) selectedMetric: 'all' | 'damage' | 'hit' | 'movement' = 'all';

  @state() private hoveredCell: HeatmapCell | null = null;
  @state() private selectedCell: HeatmapCell | null = null;

  @query('canvas') private canvasElement!: HTMLCanvasElement;

  firstUpdated() {
    this.renderCanvas();
  }

  updated(changedProperties: PropertyValues) {
    if (
      changedProperties.has('heatmapData') ||
      changedProperties.has('selectedMetric') ||
      changedProperties.has('gridSize') ||
      changedProperties.has('cellPixelSize') ||
      changedProperties.has('selectedCell')
    ) {
      this.renderCanvas();
    }
  }

  private handleMetricChange(metric: 'all' | 'damage' | 'hit' | 'movement') {
    this.selectedMetric = metric;
    this.dispatchEvent(
      new CustomEvent('metric-changed', {
        detail: { metric },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleCanvasClick(e: MouseEvent) {
    if (!this.canvasElement) return;
    const rect = this.canvasElement.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / this.cellPixelSize);
    const y = Math.floor((e.clientY - rect.top) / this.cellPixelSize);

    const cell = this.heatmapData?.cells.find((c) => c.x === x && c.y === y) || {
      x,
      y,
      density: 0,
      movement_count: 0,
      damage_total: 0,
      hit_count: 0,
      knockout_count: 0,
    };

    this.selectedCell = cell;
    this.dispatchEvent(
      new CustomEvent('cell-selected', {
        detail: { cell },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleCanvasMouseMove(e: MouseEvent) {
    if (!this.canvasElement) return;
    const rect = this.canvasElement.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / this.cellPixelSize);
    const y = Math.floor((e.clientY - rect.top) / this.cellPixelSize);

    const cell = this.heatmapData?.cells.find((c) => c.x === x && c.y === y);
    this.hoveredCell = cell || null;
  }

  private handleCanvasMouseLeave() {
    this.hoveredCell = null;
  }

  private renderCanvas() {
    const canvas = this.canvasElement;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = this.gridSize * this.cellPixelSize;
    const height = this.gridSize * this.cellPixelSize;
    canvas.width = width;
    canvas.height = height;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    this.drawGridLines(ctx, width, height);
    this.drawDensityCells(ctx);
    this.drawCorridors(ctx);
    this.drawHazards(ctx);
    this.drawKnockouts(ctx);
    this.drawSelection(ctx);
  }

  private drawGridLines(ctx: CanvasRenderingContext2D, width: number, height: number) {
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += this.cellPixelSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += this.cellPixelSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  private getCellColor(val: number, max: number): string {
    if (val <= 0 || max <= 0) return 'rgba(0, 0, 0, 0)';
    const ratio = Math.min(val / max, 1);
    if (ratio < 0.25) return `rgba(42, 157, 143, ${0.3 + ratio * 0.4})`; // Teal
    if (ratio < 0.5) return `rgba(233, 196, 106, ${0.4 + ratio * 0.5})`; // Yellow
    if (ratio < 0.75) return `rgba(244, 162, 97, ${0.5 + ratio * 0.4})`; // Orange
    return `rgba(230, 57, 70, ${0.6 + ratio * 0.4})`; // Crimson
  }

  private drawDensityCells(ctx: CanvasRenderingContext2D) {
    if (!this.heatmapData?.cells?.length) return;
    const cells = this.heatmapData.cells;
    const maxVal = Math.max(
      ...cells.map((c) => {
        if (this.selectedMetric === 'damage') return c.damage_total;
        if (this.selectedMetric === 'hit') return c.hit_count;
        if (this.selectedMetric === 'movement') return c.movement_count;
        return c.density || 1;
      }),
      1
    );

    for (const cell of cells) {
      let metricVal = cell.density;
      if (this.selectedMetric === 'damage') metricVal = cell.damage_total;
      else if (this.selectedMetric === 'hit') metricVal = cell.hit_count;
      else if (this.selectedMetric === 'movement') metricVal = cell.movement_count;

      if (metricVal > 0) {
        ctx.fillStyle = this.getCellColor(metricVal, maxVal);
        ctx.fillRect(
          cell.x * this.cellPixelSize + 1,
          cell.y * this.cellPixelSize + 1,
          this.cellPixelSize - 2,
          this.cellPixelSize - 2
        );
      }
    }
  }

  private drawCorridors(ctx: CanvasRenderingContext2D) {
    const corridors: MovementCorridor[] = this.heatmapData?.corridors || [];
    if (!corridors.length) return;

    ctx.strokeStyle = '#2a9d8f';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([4, 4]);

    for (const c of corridors) {
      const startX = c.fromX * this.cellPixelSize + this.cellPixelSize / 2;
      const startY = c.fromY * this.cellPixelSize + this.cellPixelSize / 2;
      const endX = c.toX * this.cellPixelSize + this.cellPixelSize / 2;
      const endY = c.toY * this.cellPixelSize + this.cellPixelSize / 2;

      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      ctx.fillStyle = '#2a9d8f';
      ctx.beginPath();
      ctx.arc(endX, endY, 3, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.setLineDash([]);
  }

  private drawHazards(ctx: CanvasRenderingContext2D) {
    const hazards: HazardHotspot[] = this.heatmapData?.hazards || [];
    for (const h of hazards) {
      const px = h.x * this.cellPixelSize;
      const py = h.y * this.cellPixelSize;

      ctx.fillStyle = 'rgba(231, 111, 81, 0.35)';
      ctx.fillRect(px + 2, py + 2, this.cellPixelSize - 4, this.cellPixelSize - 4);

      ctx.strokeStyle = '#e76f51';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(px + 2, py + 2, this.cellPixelSize - 4, this.cellPixelSize - 4);

      ctx.fillStyle = '#e76f51';
      ctx.font = 'bold 10px monospace';
      ctx.fillText('⚠', px + 4, py + 12);
    }
  }

  private drawKnockouts(ctx: CanvasRenderingContext2D) {
    const knockouts: KnockoutLocation[] = this.heatmapData?.knockouts || [];
    for (const k of knockouts) {
      const px = k.x * this.cellPixelSize;
      const py = k.y * this.cellPixelSize;

      ctx.fillStyle = '#121212';
      ctx.font = '14px sans-serif';
      ctx.fillText('💀', px + this.cellPixelSize / 4, py + (this.cellPixelSize * 3) / 4);
    }
  }

  private drawSelection(ctx: CanvasRenderingContext2D) {
    if (!this.selectedCell) return;
    const px = this.selectedCell.x * this.cellPixelSize;
    const py = this.selectedCell.y * this.cellPixelSize;

    ctx.strokeStyle = '#121212';
    ctx.lineWidth = 3;
    ctx.strokeRect(px, py, this.cellPixelSize, this.cellPixelSize);
  }

  render() {
    const activeCell = this.hoveredCell || this.selectedCell;

    return html`
      <div class="heatmap-header">
        <div class="heatmap-title">
          <span>Spatial Combat Heatmap</span>
        </div>
        <div class="metric-filters">
          <button
            class="filter-btn ${this.selectedMetric === 'all' ? 'active' : ''}"
            @click=${() => this.handleMetricChange('all')}
          >
            All Weights
          </button>
          <button
            class="filter-btn ${this.selectedMetric === 'damage' ? 'active' : ''}"
            @click=${() => this.handleMetricChange('damage')}
          >
            Damage
          </button>
          <button
            class="filter-btn ${this.selectedMetric === 'hit' ? 'active' : ''}"
            @click=${() => this.handleMetricChange('hit')}
          >
            Strikes
          </button>
          <button
            class="filter-btn ${this.selectedMetric === 'movement' ? 'active' : ''}"
            @click=${() => this.handleMetricChange('movement')}
          >
            Traffic
          </button>
        </div>
      </div>

      <div class="canvas-container">
        <canvas
          @click=${this.handleCanvasClick}
          @mousemove=${this.handleCanvasMouseMove}
          @mouseleave=${this.handleCanvasMouseLeave}
        ></canvas>
      </div>

      <div class="legend-bar">
        <div class="legend-scale">
          <span>Low Density</span>
          <div class="scale-gradient"></div>
          <span>Lethal</span>
        </div>
        <div class="legend-items">
          <div class="legend-badge">
            <span style="color: #2a9d8f; font-weight: bold;">--</span>
            <span>Corridors</span>
          </div>
          <div class="legend-badge">
            <span>⚠</span>
            <span>Hazards</span>
          </div>
          <div class="legend-badge">
            <span>💀</span>
            <span>Knockouts</span>
          </div>
        </div>
      </div>

      ${activeCell
        ? html`
            <div class="inspector-card">
              <span class="inspector-title">Cell (${activeCell.x}, ${activeCell.y})</span>
              <div class="inspector-stats">
                <span class="stat-pill">Damage: ${activeCell.damage_total || 0}</span>
                <span class="stat-pill">Hits: ${activeCell.hit_count || 0}</span>
                <span class="stat-pill">Traffic: ${activeCell.movement_count || 0}</span>
                <span class="stat-pill">Knockouts: ${activeCell.knockout_count || 0}</span>
              </div>
            </div>
          `
        : html`
            <div class="inspector-card">
              <span class="inspector-title">Inspect Map Coordinates</span>
              <div class="inspector-stats">
                <span>Click or hover over any grid cell to view tactical breakdown.</span>
              </div>
            </div>
          `}
    `;
  }
}
