import { html, svg, type TemplateResult } from 'lit';
import type { AtlasTerritory } from './types.ts';

export interface TerritoryRendererProps {
  territories: AtlasTerritory[];
  activeLayer: string;
  activeEra?: string;
  showContestedOnly?: boolean;
}

export function filterVisibleTerritories(
  territories: AtlasTerritory[],
  activeLayer: string,
  activeEra?: string,
  showContestedOnly?: boolean
): AtlasTerritory[] {
  return territories.filter((t) => {
    if (showContestedOnly && !t.is_contested) return false;
    if (activeEra && t.era && !t.era.toLowerCase().includes(activeEra.toLowerCase())) {
      return false;
    }
    return t.layer === activeLayer || t.layer === 'continental';
  });
}

export function renderTerritoryDefs(): TemplateResult {
  return svg`
    <pattern id="contested-hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="8" stroke="#e63946" stroke-width="2" />
    </pattern>
  `;
}

export function renderTerritories(props: TerritoryRendererProps): TemplateResult {
  const visibleTerritories = filterVisibleTerritories(
    props.territories,
    props.activeLayer,
    props.activeEra,
    props.showContestedOnly
  );

  return html`
    <g class="territories-layer">
      ${visibleTerritories.map((t) => {
        const points = t.polygon_coordinates.map((p) => `${p[0]},${p[1]}`).join(' ');
        const fill = t.metadata?.banner_color || '#457b9d';
        return html`
          <polygon
            points=${points}
            class="territory-poly ${t.is_contested ? 'contested' : ''}"
            style="fill: ${fill};"
            data-territory-id=${t.territory_id}
            data-name=${t.name}
          />
        `;
      })}
    </g>
  `;
}
