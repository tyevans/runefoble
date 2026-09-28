import { html, type TemplateResult } from 'lit';
import type { RadialActionItem } from '../board-types.ts';
import { renderBauhausGlyph } from './radial_glyphs.ts';

export const RADIAL_ACTIONS: RadialActionItem[] = [
  { id: 'attack', label: 'Attack', icon: 'attack', color: 'var(--rf-accent-primary, #e63946)', description: 'Execute melee or ranged weapon strike' },
  { id: 'dash', label: 'Dash', icon: 'dash', color: 'var(--rf-accent-tertiary, #ffb703)', description: 'Double movement budget for the turn' },
  { id: 'disengage', label: 'Disengage', icon: 'disengage', color: 'var(--rf-accent-secondary, #1d3557)', description: 'Movement does not provoke opportunity attacks' },
  { id: 'dodge', label: 'Dodge', icon: 'dodge', color: '#2a9d8f', description: 'Attacks against you have disadvantage until next turn' },
  { id: 'cast', label: 'Cast', icon: 'cast', color: '#9d4edd', description: 'Cast an AoE spell or tactical cantrip' },
];

export function polarToCartesian(centerX: number, centerY: number, radius: number, angleInRadians: number): { x: number; y: number } {
  return {
    x: Math.round(centerX + radius * Math.cos(angleInRadians)),
    y: Math.round(centerY + radius * Math.sin(angleInRadians)),
  };
}

export function describeArc(x: number, y: number, radius: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(x, y, radius, endAngle);
  const end = polarToCartesian(x, y, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= Math.PI ? '0' : '1';
  return ['M', start.x, start.y, 'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(' ');
}

export function calculateWedgePosition(index: number, count: number, radius: number, startAngle = -Math.PI / 2): { x: number; y: number } {
  const angleStep = (2 * Math.PI) / count;
  const angle = startAngle + index * angleStep;
  return polarToCartesian(0, 0, radius, angle);
}

export interface WedgeProps {
  action: RadialActionItem;
  isActive: boolean;
  x: number;
  y: number;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onPointerDown: (e: PointerEvent) => void;
  onPointerUp: (e: PointerEvent) => void;
  onClick: (e: Event) => void;
}

export function renderWedge(props: WedgeProps): TemplateResult {
  const { action, isActive, x, y, onMouseEnter, onMouseLeave, onPointerDown, onPointerUp, onClick } = props;
  return html`
    <div
      class="action-wedge ${isActive ? 'active' : ''}"
      style="left: ${x}px; top: ${y}px; background: ${action.color};"
      @mouseenter="${onMouseEnter}"
      @mouseleave="${onMouseLeave}"
      @pointerdown="${onPointerDown}"
      @pointerup="${onPointerUp}"
      @click="${onClick}"
      title="${action.label}: ${action.description}"
      role="button"
      tabindex="0"
    >
      ${renderBauhausGlyph(action.icon)}
      <span class="action-label">${action.label}</span>
    </div>
  `;
}
