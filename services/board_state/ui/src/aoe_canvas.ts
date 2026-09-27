import { css, svg } from 'lit';
import type { SVGTemplateResult } from 'lit';
import { CONE_SPREAD_DEG } from './aoe_geometry.ts';
import type { AoEHandleEvents, AoERenderPaths, AoEShape, AoETemplateConfig } from './aoe_types.ts';

export const aoeTemplateStyles = css`
  :host {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 50;
    user-select: none;
    -webkit-user-select: none;
  }
  svg { width: 100%; height: 100%; overflow: visible; }
  .aoe-shape {
    fill: rgba(230, 57, 70, 0.28);
    stroke: var(--rf-accent-primary, #e63946);
    stroke-width: 2.5px;
    stroke-dasharray: 6 3;
    animation: dash-pulse 2s linear infinite;
    transition: d 0.05s ease-out;
  }
  .aoe-shape.sphere { fill: rgba(255, 183, 3, 0.25); stroke: var(--rf-accent-tertiary, #ffb703); }
  .aoe-shape.line { fill: rgba(69, 123, 157, 0.28); stroke: var(--rf-accent-secondary, #1d3557); }
  .aoe-shape.cube { fill: rgba(42, 157, 143, 0.28); stroke: var(--rf-accent-primary, #2a9d8f); }
  @keyframes dash-pulse { to { stroke-dashoffset: -18; } }
  .handle {
    pointer-events: auto;
    cursor: grab;
    filter: drop-shadow(2px 2px 0px rgba(18, 18, 18, 0.8));
    transition: transform 0.1s ease;
  }
  .handle:hover, .handle:active { cursor: grabbing; transform: scale(1.2); }
  .origin-handle { fill: #ffffff; stroke: var(--rf-border-color, #121212); stroke-width: 2.5px; }
  .rotation-handle { fill: var(--rf-accent-tertiary, #ffb703); stroke: var(--rf-border-color, #121212); stroke-width: 2.5px; }
  .angle-badge {
    font-family: var(--rf-font-family, system-ui, sans-serif);
    font-size: 11px;
    font-weight: 800;
    fill: #ffffff;
    stroke: #121212;
    stroke-width: 0.5px;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
  }
  .badge-bg { fill: #121212; rx: 3px; }
`;

export function renderAoEShape(
  shape: AoEShape,
  ox: number,
  oy: number,
  rad: number,
  scalePx: number,
  config: Pick<AoETemplateConfig, 'radiusFt' | 'lengthFt' | 'widthFt'>
): AoERenderPaths {
  let shapeSvg = svg``;
  let rotHandleX = ox;
  let rotHandleY = oy;

  if (shape === 'cone') {
    const r = (config.radiusFt || 15) * scalePx;
    const halfSpread = ((CONE_SPREAD_DEG / 2) * Math.PI) / 180;
    const a1 = rad - halfSpread;
    const a2 = rad + halfSpread;
    const x1 = ox + r * Math.cos(a1);
    const y1 = oy + r * Math.sin(a1);
    const x2 = ox + r * Math.cos(a2);
    const y2 = oy + r * Math.sin(a2);
    shapeSvg = svg`<path class="aoe-shape cone" d="M ${ox} ${oy} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z" />`;
    rotHandleX = ox + r * Math.cos(rad);
    rotHandleY = oy + r * Math.sin(rad);
  } else if (shape === 'sphere') {
    const r = (config.radiusFt || 20) * scalePx;
    shapeSvg = svg`<circle class="aoe-shape sphere" cx="${ox}" cy="${oy}" r="${r}" />`;
    rotHandleX = ox + r * Math.cos(rad);
    rotHandleY = oy + r * Math.sin(rad);
  } else if (shape === 'line') {
    const len = (config.lengthFt || 30) * scalePx;
    const w = (config.widthFt || 5) * scalePx;
    const ux = Math.cos(rad);
    const uy = Math.sin(rad);
    const vx = -Math.sin(rad) * (w / 2);
    const vy = Math.cos(rad) * (w / 2);
    const p1x = ox + vx; const p1y = oy + vy;
    const p2x = ox - vx; const p2y = oy - vy;
    const p3x = ox + len * ux - vx; const p3y = oy + len * uy - vy;
    const p4x = ox + len * ux + vx; const p4y = oy + len * uy + vy;
    shapeSvg = svg`<path class="aoe-shape line" d="M ${p1x} ${p1y} L ${p2x} ${p2y} L ${p3x} ${p3y} L ${p4x} ${p4y} Z" />`;
    rotHandleX = ox + len * ux;
    rotHandleY = oy + len * uy;
  } else if (shape === 'cube') {
    const h = ((config.lengthFt || config.radiusFt || 20) * scalePx) / 2;
    const ux = Math.cos(rad); const uy = Math.sin(rad);
    const vx = -Math.sin(rad); const vy = Math.cos(rad);
    const p1x = ox - h * ux - h * vx; const p1y = oy - h * uy - h * vy;
    const p2x = ox + h * ux - h * vx; const p2y = oy + h * uy - h * vy;
    const p3x = ox + h * ux + h * vx; const p3y = oy + h * uy + h * vy;
    const p4x = ox - h * ux + h * vx; const p4y = oy - h * uy + h * vy;
    shapeSvg = svg`<path class="aoe-shape cube" d="M ${p1x} ${p1y} L ${p2x} ${p2y} L ${p3x} ${p3y} L ${p4x} ${p4y} Z" />`;
    rotHandleX = ox + h * ux;
    rotHandleY = oy + h * uy;
  }
  return { shapeSvg, rotHandleX, rotHandleY };
}

export function renderAoEHandles(
  ox: number,
  oy: number,
  rotHandleX: number,
  rotHandleY: number,
  directionDeg: number,
  handlers: AoEHandleEvents
): SVGTemplateResult {
  return svg`
    <line x1="${ox}" y1="${oy}" x2="${rotHandleX}" y2="${rotHandleY}" stroke="var(--rf-border-color, #121212)" stroke-width="1.5" stroke-dasharray="3 3" />
    <g class="handle" @pointerdown="${handlers.onRotationDown}" @pointermove="${handlers.onRotationMove}" @pointerup="${handlers.onRotationUp}">
      <circle class="rotation-handle" cx="${rotHandleX}" cy="${rotHandleY}" r="11" />
      <rect class="badge-bg" x="${rotHandleX + 14}" y="${rotHandleY - 10}" width="36" height="20" />
      <text class="angle-badge" x="${rotHandleX + 32}" y="${rotHandleY}">${Math.round(directionDeg)}°</text>
    </g>
    <g class="handle" @pointerdown="${handlers.onOriginDown}" @pointermove="${handlers.onOriginMove}" @pointerup="${handlers.onOriginUp}">
      <circle class="origin-handle" cx="${ox}" cy="${oy}" r="10" />
      <circle cx="${ox}" cy="${oy}" r="3" fill="var(--rf-accent-primary, #e63946)" />
    </g>
  `;
}
