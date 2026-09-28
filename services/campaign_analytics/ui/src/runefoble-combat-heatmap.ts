/**
 * Lit Web Component: <runefoble-combat-heatmap>
 * Governed by ADR-0004, ADR-0007, ADR-0012, and ADR-0013.
 */

import { LitElement, html, type PropertyValues } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';
import { combatHeatmapStyles } from './runefoble-combat-heatmap.styles.ts';
import type { CampaignHeatmapResponse, HeatmapCell } from './types.ts';
import { renderHeatmapCanvas, type MetricType } from './heatmap/canvas-renderer.ts';
import { renderHeatmapHeader, renderHeatmapLegend } from './heatmap/heatmap-controls.template.ts';
import { renderCellInspector } from './heatmap/cell-inspector.template.ts';

@customElement('runefoble-combat-heatmap')
export class RunefobleCombatHeatmap extends LitElement {
  static styles = [combatHeatmapStyles];

  @property({ type: Object }) heatmapData: CampaignHeatmapResponse | null = null;
  @property({ type: Number }) gridSize = 10;
  @property({ type: Number }) cellPixelSize = 36;
  @property({ type: String }) selectedMetric: MetricType = 'all';

  @state() private hoveredCell: HeatmapCell | null = null;
  @state() private selectedCell: HeatmapCell | null = null;
  @query('canvas') private canvasElement!: HTMLCanvasElement;
  private resizeObserver: ResizeObserver | null = null;

  firstUpdated() {
    this.renderCanvas();
    const container = this.shadowRoot?.querySelector('.canvas-container');
    if (container && typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => this.renderCanvas());
      this.resizeObserver.observe(container);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.resizeObserver?.disconnect();
  }

  updated(props: PropertyValues) {
    if (['heatmapData', 'selectedMetric', 'gridSize', 'cellPixelSize', 'selectedCell'].some((k) => props.has(k))) {
      this.renderCanvas();
    }
  }

  private handleMetricChange(metric: MetricType) {
    this.selectedMetric = metric;
    this.dispatchEvent(new CustomEvent('metric-changed', { detail: { metric }, bubbles: true, composed: true }));
  }

  private handleCanvasClick(e: MouseEvent) {
    if (!this.canvasElement) return;
    const rect = this.canvasElement.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / this.cellPixelSize);
    const y = Math.floor((e.clientY - rect.top) / this.cellPixelSize);
    const cell = this.heatmapData?.cells.find((c) => c.x === x && c.y === y) || {
      x, y, density: 0, movement_count: 0, damage_total: 0, hit_count: 0, knockout_count: 0,
    };
    this.selectedCell = cell;
    this.dispatchEvent(new CustomEvent('cell-selected', { detail: { cell }, bubbles: true, composed: true }));
  }

  private handleCanvasMouseMove(e: MouseEvent) {
    if (!this.canvasElement) return;
    const rect = this.canvasElement.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / this.cellPixelSize);
    const y = Math.floor((e.clientY - rect.top) / this.cellPixelSize);
    this.hoveredCell = this.heatmapData?.cells.find((c) => c.x === x && c.y === y) || null;
  }

  private handleCanvasMouseLeave() {
    this.hoveredCell = null;
  }

  private renderCanvas() {
    if (!this.canvasElement) return;
    renderHeatmapCanvas({
      canvas: this.canvasElement,
      gridSize: this.gridSize,
      cellPixelSize: this.cellPixelSize,
      selectedMetric: this.selectedMetric,
      heatmapData: this.heatmapData,
      selectedCell: this.selectedCell,
    });
  }

  render() {
    const activeCell = this.hoveredCell || this.selectedCell;
    return html`
      ${renderHeatmapHeader({
        selectedMetric: this.selectedMetric,
        onMetricChange: (m) => this.handleMetricChange(m),
        totalPoints: this.heatmapData?.total_points,
      })}
      <div class="canvas-container">
        <canvas
          @click=${this.handleCanvasClick}
          @mousemove=${this.handleCanvasMouseMove}
          @mouseleave=${this.handleCanvasMouseLeave}
        ></canvas>
      </div>
      ${renderHeatmapLegend(this.heatmapData?.max_density)}
      ${renderCellInspector({ cell: activeCell, knockouts: this.heatmapData?.knockouts })}
    `;
  }
}
