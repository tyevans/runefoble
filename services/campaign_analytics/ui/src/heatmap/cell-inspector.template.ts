import { html, type TemplateResult } from 'lit';
import type { HeatmapCell, KnockoutLocation } from '../types.ts';

export interface CellInspectorProps {
  cell: HeatmapCell | null;
  knockouts?: KnockoutLocation[];
}

export function renderCellInspector(props: CellInspectorProps): TemplateResult {
  const { cell, knockouts = [] } = props;
  if (!cell) {
    return html`
      <div class="inspector-card">
        <span class="inspector-title">Inspect Map Coordinates</span>
        <div class="inspector-stats">
          <span>Click or hover over any grid cell to view tactical breakdown.</span>
        </div>
      </div>
    `;
  }

  const casualties = knockouts.filter((k) => k.x === cell.x && k.y === cell.y);

  return html`
    <div class="inspector-card">
      <span class="inspector-title">Cell (${cell.x}, ${cell.y})</span>
      <div class="inspector-stats">
        <span class="stat-pill">Damage: ${cell.damage_total || 0}</span>
        <span class="stat-pill">Hits: ${cell.hit_count || 0}</span>
        <span class="stat-pill">Traffic: ${cell.movement_count || 0}</span>
        <span class="stat-pill">Knockouts: ${cell.knockout_count || 0}</span>
        ${casualties.map((k) => html`<span class="stat-pill">Casualty: ${k.characterName} (R${k.round})</span>`)}
      </div>
    </div>
  `;
}
