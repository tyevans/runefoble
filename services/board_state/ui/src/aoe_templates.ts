import { LitElement, css, html, svg } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { AoEShape, AoETemplateConfig, BoardToken } from './board-types.ts';

export const CONE_SPREAD_DEG = 53.13; // Standard 5e cone spread angle

export function snapAngle(deg: number, increment = 15): number {
  if (increment <= 0) return (deg % 360 + 360) % 360;
  const snapped = Math.round(deg / increment) * increment;
  return (snapped % 360 + 360) % 360;
}

export function normalizeAngleDiff(angle1: number, angle2: number): number {
  return Math.abs(((angle1 - angle2 + 180) % 360 + 360) % 360 - 180);
}

export function isPointInAoEGeometry(
  targetFtX: number,
  targetFtY: number,
  config: AoETemplateConfig
): boolean {
  const { shape, originX, originY, directionDeg, radiusFt = 15, lengthFt = 30, widthFt = 5 } = config;
  const origFtX = originX * 5.0;
  const origFtY = originY * 5.0;
  const dx = targetFtX - origFtX;
  const dy = targetFtY - origFtY;
  const dist = Math.hypot(dx, dy);

  if (shape === 'cone') {
    if (dist <= 0.001) return true;
    if (dist > radiusFt + 0.05) return false;
    const ptAngle = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
    const angleDiff = normalizeAngleDiff(ptAngle, directionDeg);
    return angleDiff <= CONE_SPREAD_DEG / 2 + 0.05;
  }

  if (shape === 'sphere') {
    return dist <= (radiusFt || 20) + 0.05;
  }

  if (shape === 'line') {
    const rad = (directionDeg * Math.PI) / 180;
    const ux = Math.cos(rad);
    const uy = Math.sin(rad);
    const vx = -Math.sin(rad);
    const vy = Math.cos(rad);

    const projAlong = dx * ux + dy * uy;
    const projPerp = Math.abs(dx * vx + dy * vy);

    return projAlong >= -0.05 && projAlong <= (lengthFt || 30) + 0.05 && projPerp <= widthFt / 2 + 0.05;
  }

  return false;
}

export function isTokenInAoE(token: BoardToken, config: AoETemplateConfig): boolean {
  const targetFtX = (token.x + 0.5) * 5.0;
  const targetFtY = (token.y + 0.5) * 5.0;
  return isPointInAoEGeometry(targetFtX, targetFtY, config);
}

export function computeAffectedTokens(tokens: BoardToken[], config: AoETemplateConfig): string[] {
  return tokens.filter((t) => isTokenInAoE(t, config)).map((t) => t.id);
}

export function computeAffectedCells(
  cols: number,
  rows: number,
  config: AoETemplateConfig
): [number, number][] {
  const affected: [number, number][] = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const cellFtX = (x + 0.5) * 5.0;
      const cellFtY = (y + 0.5) * 5.0;
      if (isPointInAoEGeometry(cellFtX, cellFtY, config)) {
        affected.push([x, y]);
      }
    }
  }
  return affected;
}

@customElement('runefoble-aoe-template')
export class RunefobleAoETemplate extends LitElement {
  static styles = css`
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

    svg {
      width: 100%;
      height: 100%;
      overflow: visible;
    }

    .aoe-shape {
      fill: rgba(230, 57, 70, 0.28);
      stroke: var(--rf-accent-primary, #e63946);
      stroke-width: 2.5px;
      stroke-dasharray: 6 3;
      animation: dash-pulse 2s linear infinite;
      transition: d 0.05s ease-out;
    }

    .aoe-shape.sphere {
      fill: rgba(255, 183, 3, 0.25);
      stroke: var(--rf-accent-tertiary, #ffb703);
    }

    .aoe-shape.line {
      fill: rgba(69, 123, 157, 0.28);
      stroke: var(--rf-accent-secondary, #1d3557);
    }

    @keyframes dash-pulse {
      to {
        stroke-dashoffset: -18;
      }
    }

    .handle {
      pointer-events: auto;
      cursor: grab;
      filter: drop-shadow(2px 2px 0px rgba(18, 18, 18, 0.8));
      transition: transform 0.1s ease;
    }

    .handle:hover,
    .handle:active {
      cursor: grabbing;
      transform: scale(1.2);
    }

    .origin-handle {
      fill: #ffffff;
      stroke: var(--rf-border-color, #121212);
      stroke-width: 2.5px;
    }

    .rotation-handle {
      fill: var(--rf-accent-tertiary, #ffb703);
      stroke: var(--rf-border-color, #121212);
      stroke-width: 2.5px;
    }

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

    .badge-bg {
      fill: #121212;
      rx: 3px;
    }
  `;

  @property({ type: String }) shape: AoEShape = 'cone';
  @property({ type: Number }) originX = 2; // grid coords
  @property({ type: Number }) originY = 2;
  @property({ type: Number }) directionDeg = 0;
  @property({ type: Number }) radiusFt = 15;
  @property({ type: Number }) lengthFt = 30;
  @property({ type: Number }) widthFt = 5;
  @property({ type: Number }) cellSizePx = 56;
  @property({ type: String }) spellName = 'Burning Hands';
  @property({ type: Array }) tokens: BoardToken[] = [];
  @property({ type: Number }) cols = 8;
  @property({ type: Number }) rows = 8;
  @property({ type: Boolean }) interactive = true;

  @state() private isDraggingOrigin = false;
  @state() private isDraggingRotation = false;

  private notifyChange() {
    const config: AoETemplateConfig = {
      shape: this.shape,
      originX: this.originX,
      originY: this.originY,
      directionDeg: this.directionDeg,
      radiusFt: this.radiusFt,
      lengthFt: this.lengthFt,
      widthFt: this.widthFt,
      spellName: this.spellName,
    };
    const affectedTokenIds = computeAffectedTokens(this.tokens, config);
    const affectedCells = computeAffectedCells(this.cols, this.rows, config);

    this.dispatchEvent(
      new CustomEvent('aoe-change', {
        detail: { config, affectedTokenIds, affectedCells },
        bubbles: true,
        composed: true,
      })
    );
  }

  firstUpdated() {
    this.notifyChange();
  }

  private handleOriginPointerDown(e: PointerEvent) {
    if (!this.interactive || e.button !== 0) return;
    e.stopPropagation();
    this.isDraggingOrigin = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }

  private handleOriginPointerMove(e: PointerEvent) {
    if (!this.isDraggingOrigin) return;
    const parentRect = this.getBoundingClientRect();
    const relX = e.clientX - parentRect.left;
    const relY = e.clientY - parentRect.top;

    // Grid snap in half-cell (2.5ft) or integer increments
    const gridX = Math.max(0, Math.min(this.cols, Math.round((relX / this.cellSizePx) * 2) / 2));
    const gridY = Math.max(0, Math.min(this.rows, Math.round((relY / this.cellSizePx) * 2) / 2));

    if (gridX !== this.originX || gridY !== this.originY) {
      this.originX = gridX;
      this.originY = gridY;
      this.notifyChange();
    }
  }

  private handleOriginPointerUp(e: PointerEvent) {
    if (this.isDraggingOrigin) {
      this.isDraggingOrigin = false;
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {}
      this.notifyChange();
    }
  }

  private handleRotationPointerDown(e: PointerEvent) {
    if (!this.interactive || e.button !== 0) return;
    e.stopPropagation();
    this.isDraggingRotation = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }

  private handleRotationPointerMove(e: PointerEvent) {
    if (!this.isDraggingRotation) return;
    const parentRect = this.getBoundingClientRect();
    const originPxX = this.originX * this.cellSizePx;
    const originPxY = this.originY * this.cellSizePx;
    const clientX = e.clientX - parentRect.left;
    const clientY = e.clientY - parentRect.top;

    const rawAngle = (Math.atan2(clientY - originPxY, clientX - originPxX) * 180) / Math.PI;
    const snapped = snapAngle(rawAngle, 15);

    if (snapped !== this.directionDeg) {
      this.directionDeg = snapped;
      this.notifyChange();
    }
  }

  private handleRotationPointerUp(e: PointerEvent) {
    if (this.isDraggingRotation) {
      this.isDraggingRotation = false;
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {}
      this.notifyChange();
    }
  }

  render() {
    const scalePx = this.cellSizePx / 5.0; // px per foot
    const ox = this.originX * this.cellSizePx;
    const oy = this.originY * this.cellSizePx;
    const rad = (this.directionDeg * Math.PI) / 180;

    let shapeSvg = svg``;
    let rotHandleX = ox;
    let rotHandleY = oy;

    if (this.shape === 'cone') {
      const r = (this.radiusFt || 15) * scalePx;
      const halfSpreadRad = ((CONE_SPREAD_DEG / 2) * Math.PI) / 180;
      const a1 = rad - halfSpreadRad;
      const a2 = rad + halfSpreadRad;
      const x1 = ox + r * Math.cos(a1);
      const y1 = oy + r * Math.sin(a1);
      const x2 = ox + r * Math.cos(a2);
      const y2 = oy + r * Math.sin(a2);

      const pathData = `M ${ox} ${oy} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`;
      shapeSvg = svg`<path class="aoe-shape cone" d="${pathData}" />`;

      rotHandleX = ox + r * Math.cos(rad);
      rotHandleY = oy + r * Math.sin(rad);
    } else if (this.shape === 'sphere') {
      const r = (this.radiusFt || 20) * scalePx;
      shapeSvg = svg`<circle class="aoe-shape sphere" cx="${ox}" cy="${oy}" r="${r}" />`;

      rotHandleX = ox + r * Math.cos(rad);
      rotHandleY = oy + r * Math.sin(rad);
    } else if (this.shape === 'line') {
      const len = (this.lengthFt || 30) * scalePx;
      const w = (this.widthFt || 5) * scalePx;
      const ux = Math.cos(rad);
      const uy = Math.sin(rad);
      const vx = -Math.sin(rad) * (w / 2);
      const vy = Math.cos(rad) * (w / 2);

      const p1x = ox + vx;
      const p1y = oy + vy;
      const p2x = ox - vx;
      const p2y = oy - vy;
      const p3x = ox + len * ux - vx;
      const p3y = oy + len * uy - vy;
      const p4x = ox + len * ux + vx;
      const p4y = oy + len * uy + vy;

      const pathData = `M ${p1x} ${p1y} L ${p2x} ${p2y} L ${p3x} ${p3y} L ${p4x} ${p4y} Z`;
      shapeSvg = svg`<path class="aoe-shape line" d="${pathData}" />`;

      rotHandleX = ox + len * ux;
      rotHandleY = oy + len * uy;
    }

    return html`
      <svg>
        ${shapeSvg}

        ${this.interactive
          ? svg`
            <!-- Direction Indicator Line -->
            <line
              x1="${ox}"
              y1="${oy}"
              x2="${rotHandleX}"
              y2="${rotHandleY}"
              stroke="var(--rf-border-color, #121212)"
              stroke-width="1.5"
              stroke-dasharray="3 3"
            />

            <!-- Rotation Handle -->
            <g
              class="handle"
              @pointerdown="${(e: PointerEvent) => this.handleRotationPointerDown(e)}"
              @pointermove="${(e: PointerEvent) => this.handleRotationPointerMove(e)}"
              @pointerup="${(e: PointerEvent) => this.handleRotationPointerUp(e)}"
            >
              <circle
                class="rotation-handle"
                cx="${rotHandleX}"
                cy="${rotHandleY}"
                r="11"
              />
              <rect
                class="badge-bg"
                x="${rotHandleX + 14}"
                y="${rotHandleY - 10}"
                width="36"
                height="20"
              />
              <text
                class="angle-badge"
                x="${rotHandleX + 32}"
                y="${rotHandleY}"
              >${Math.round(this.directionDeg)}°</text>
            </g>

            <!-- Origin Handle -->
            <g
              class="handle"
              @pointerdown="${(e: PointerEvent) => this.handleOriginPointerDown(e)}"
              @pointermove="${(e: PointerEvent) => this.handleOriginPointerMove(e)}"
              @pointerup="${(e: PointerEvent) => this.handleOriginPointerUp(e)}"
            >
              <circle
                class="origin-handle"
                cx="${ox}"
                cy="${oy}"
                r="10"
              />
              <circle cx="${ox}" cy="${oy}" r="3" fill="var(--rf-accent-primary, #e63946)" />
            </g>
          `
          : null}
      </svg>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-aoe-template': RunefobleAoETemplate;
  }
}
