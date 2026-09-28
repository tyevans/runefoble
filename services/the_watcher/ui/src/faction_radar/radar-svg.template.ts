import { html, svg, type TemplateResult } from 'lit';
import type { FactionData } from './types.ts';

export interface RadarSvgProps {
  factions: FactionData[];
  selectedFactionId?: string;
  onSelectFaction: (faction: FactionData) => void;
}

export function renderRadarChart(props: RadarSvgProps): TemplateResult {
  const { factions, selectedFactionId, onSelectFaction } = props;
  if (factions.length < 3) {
    return html`
      <div class="radar-card">
        <div class="radar-title">Influence Gauge Matrix</div>
        <div class="empty-state">
          ${factions.length === 0
            ? 'No factions registered in campaign.'
            : `${factions.length} faction(s) monitored (radar requires 3+ for polygon projection).`}
        </div>
      </div>
    `;
  }

  const cx = 150;
  const cy = 150;
  const radius = 100;
  const numPoints = factions.length;
  const angleStep = (2 * Math.PI) / numPoints;
  const rings = [0.25, 0.5, 0.75, 1.0];

  const axes = factions.map((f, i) => {
    const angle = -Math.PI / 2 + i * angleStep;
    return {
      faction: f,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      labelX: cx + (radius + 20) * Math.cos(angle),
      labelY: cy + (radius + 20) * Math.sin(angle) + 4,
    };
  });

  const polygonPoints = factions
    .map((f, i) => {
      const inf = Math.max(5, Math.min(100, f.influence));
      const r = (inf / 100) * radius;
      const angle = -Math.PI / 2 + i * angleStep;
      return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
    })
    .join(' ');

  return html`
    <div class="radar-card">
      <div class="radar-title">Geopolitical Influence Radar</div>
      <svg class="radar-svg" viewBox="0 0 300 300">
        ${rings.map(
          (scale) => svg`
            <circle class="radar-ring" cx="${cx}" cy="${cy}" r="${(radius * scale).toFixed(1)}" />
          `
        )}
        ${axes.map(
          (axis) => svg`
            <line class="radar-axis-line" x1="${cx}" y1="${cy}" x2="${axis.x.toFixed(1)}" y2="${axis.y.toFixed(1)}" />
            <text class="radar-label" x="${axis.labelX.toFixed(1)}" y="${axis.labelY.toFixed(1)}">
              ${axis.faction.name.slice(0, 10)}
            </text>
          `
        )}
        <polygon class="radar-polygon" points="${polygonPoints}" />
        ${factions.map((f, i) => {
          const inf = Math.max(5, Math.min(100, f.influence));
          const r = (inf / 100) * radius;
          const angle = -Math.PI / 2 + i * angleStep;
          const isSelected = selectedFactionId === f.faction_id;
          return svg`
            <circle
              class="radar-node ${isSelected ? 'selected' : ''}"
              cx="${(cx + r * Math.cos(angle)).toFixed(1)}"
              cy="${(cy + r * Math.sin(angle)).toFixed(1)}"
              r="${isSelected ? 6 : 4}"
              @click="${() => onSelectFaction(f)}"
            >
              <title>${f.name}: ${f.influence}% Influence</title>
            </circle>
          `;
        })}
      </svg>
    </div>
  `;
}
