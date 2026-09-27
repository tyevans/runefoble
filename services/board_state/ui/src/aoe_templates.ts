import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { aoeTemplateStyles, renderAoEHandles, renderAoEShape } from './aoe_canvas.ts';
import { computeAffectedCells, computeAffectedTokens, snapAngle } from './aoe_geometry.ts';
import type { AoEShape, AoETemplateConfig, BoardToken } from './aoe_types.ts';

export * from './aoe_types.ts';
export * from './aoe_geometry.ts';
export * from './aoe_canvas.ts';

@customElement('runefoble-aoe-template')
export class RunefobleAoETemplate extends LitElement {
  static styles = aoeTemplateStyles;

  @property({ type: String }) shape: AoEShape = 'cone';
  @property({ type: Number }) originX = 2;
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

  firstUpdated() { this.notifyChange(); }

  private notifyChange() {
    const config: AoETemplateConfig = {
      shape: this.shape, originX: this.originX, originY: this.originY, directionDeg: this.directionDeg,
      radiusFt: this.radiusFt, lengthFt: this.lengthFt, widthFt: this.widthFt, spellName: this.spellName,
    };
    const affectedTokenIds = computeAffectedTokens(this.tokens, config);
    const affectedCells = computeAffectedCells(this.cols, this.rows, config);
    this.dispatchEvent(new CustomEvent('aoe-change', { detail: { config, affectedTokenIds, affectedCells }, bubbles: true, composed: true }));
  }

  private handleOriginDown(e: PointerEvent) {
    if (!this.interactive || e.button !== 0) return;
    e.stopPropagation(); this.isDraggingOrigin = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }
  private handleOriginMove(e: PointerEvent) {
    if (!this.isDraggingOrigin) return;
    const r = this.getBoundingClientRect();
    const gx = Math.max(0, Math.min(this.cols, Math.round(((e.clientX - r.left) / this.cellSizePx) * 2) / 2));
    const gy = Math.max(0, Math.min(this.rows, Math.round(((e.clientY - r.top) / this.cellSizePx) * 2) / 2));
    if (gx !== this.originX || gy !== this.originY) { this.originX = gx; this.originY = gy; this.notifyChange(); }
  }
  private handleOriginUp(e: PointerEvent) {
    if (!this.isDraggingOrigin) return;
    this.isDraggingOrigin = false;
    try { (e.target as HTMLElement).releasePointerCapture(e.pointerId); } catch {}
    this.notifyChange();
  }
  private handleRotationDown(e: PointerEvent) {
    if (!this.interactive || e.button !== 0) return;
    e.stopPropagation(); this.isDraggingRotation = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }
  private handleRotationMove(e: PointerEvent) {
    if (!this.isDraggingRotation) return;
    const r = this.getBoundingClientRect();
    const raw = (Math.atan2(e.clientY - r.top - this.originY * this.cellSizePx, e.clientX - r.left - this.originX * this.cellSizePx) * 180) / Math.PI;
    const snapped = snapAngle(raw, 15);
    if (snapped !== this.directionDeg) { this.directionDeg = snapped; this.notifyChange(); }
  }
  private handleRotationUp(e: PointerEvent) {
    if (!this.isDraggingRotation) return;
    this.isDraggingRotation = false;
    try { (e.target as HTMLElement).releasePointerCapture(e.pointerId); } catch {}
    this.notifyChange();
  }

  render() {
    const scalePx = this.cellSizePx / 5.0;
    const ox = this.originX * this.cellSizePx;
    const oy = this.originY * this.cellSizePx;
    const rad = (this.directionDeg * Math.PI) / 180;
    const { shapeSvg, rotHandleX, rotHandleY } = renderAoEShape(this.shape, ox, oy, rad, scalePx, this);
    const handles = this.interactive ? renderAoEHandles(ox, oy, rotHandleX, rotHandleY, this.directionDeg, {
      onOriginDown: (e) => this.handleOriginDown(e), onOriginMove: (e) => this.handleOriginMove(e), onOriginUp: (e) => this.handleOriginUp(e),
      onRotationDown: (e) => this.handleRotationDown(e), onRotationMove: (e) => this.handleRotationMove(e), onRotationUp: (e) => this.handleRotationUp(e),
    }) : null;
    return html`<svg>${shapeSvg}${handles}</svg>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-aoe-template': RunefobleAoETemplate;
  }
}
