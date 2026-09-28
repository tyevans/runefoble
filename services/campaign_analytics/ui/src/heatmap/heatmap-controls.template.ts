import { html, type TemplateResult } from 'lit';
import type { MetricType } from './canvas-renderer.ts';

export interface HeatmapControlsProps {
  selectedMetric: MetricType;
  onMetricChange: (metric: MetricType) => void;
  totalPoints?: number;
}

const METRICS: Array<{ key: MetricType; label: string }> = [
  { key: 'all', label: 'All Weights' },
  { key: 'damage', label: 'Damage' },
  { key: 'hit', label: 'Strikes' },
  { key: 'movement', label: 'Traffic' },
];

export function renderHeatmapHeader(props: HeatmapControlsProps): TemplateResult {
  const { selectedMetric, onMetricChange, totalPoints } = props;
  return html`
    <div class="heatmap-header">
      <div class="heatmap-title">
        <span>Spatial Combat Heatmap</span>
        ${totalPoints !== undefined ? html`<span class="stat-pill">Events: ${totalPoints}</span>` : ''}
      </div>
      <div class="metric-filters">
        ${METRICS.map(
          (opt) => html`
            <button
              class="filter-btn ${selectedMetric === opt.key ? 'active' : ''}"
              @click=${() => onMetricChange(opt.key)}
            >
              ${opt.label}
            </button>
          `
        )}
      </div>
    </div>
  `;
}

export function renderHeatmapLegend(maxDensity?: number): TemplateResult {
  return html`
    <div class="legend-bar">
      <div class="legend-scale">
        <span>Low Density</span>
        <div class="scale-gradient"></div>
        <span>Lethal${maxDensity !== undefined ? ` (Max: ${maxDensity})` : ''}</span>
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
  `;
}
