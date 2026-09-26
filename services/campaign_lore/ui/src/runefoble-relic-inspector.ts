import { LitElement, html, css } from 'lit';
import { customElement, property, state, query } from 'lit/decorators.js';

export interface RelicRune {
  id: string;
  inscription: string;
  position: [number, number, number];
  hitbox_radius?: number;
  translated?: string;
}

@customElement('runefoble-relic-inspector')
export class RunefobleRelicInspector extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding: 16px;
      color: var(--rf-text-primary, #121212);
      width: 520px;
      max-width: 100%;
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      box-sizing: border-box;
    }
    .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212); margin-bottom: 12px; }
    .title { font-size: 1.1rem; font-weight: 800; letter-spacing: -0.02em; }
    .badge { font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border: 1px solid var(--rf-border-color, #121212); background: var(--rf-accent-secondary, #2a9d8f); color: #ffffff; }
    .viewport {
      position: relative;
      background: #0f141d;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      height: 280px;
      overflow: hidden;
      cursor: grab;
      user-select: none;
    }
    .viewport:active {
      cursor: grabbing;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
    }
    .overlay-info {
      position: absolute;
      bottom: 8px;
      left: 8px;
      background: rgba(0, 0, 0, 0.7);
      color: #00ffcc;
      font-family: monospace;
      font-size: 0.75rem;
      padding: 4px 8px;
      border: 1px solid #00ffcc;
      pointer-events: none;
    }
    .controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
      gap: 8px;
    }
    .btn {
      padding: 6px 12px;
      font-size: 0.8rem;
      font-weight: 700;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      cursor: pointer;
      box-shadow: 2px 2px 0px #121212;
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
    }
    .btn.secondary {
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-primary, #121212);
    }
    .runes-list {
      margin-top: 12px;
      border-top: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding-top: 8px;
    }
    .runes-title {
      font-size: 0.85rem;
      font-weight: 800;
      margin-bottom: 6px;
    }
    .rune-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 10px;
      margin-bottom: 4px;
      background: #f8f9fa;
      border: 1px solid #dee2e6;
      font-size: 0.8rem;
      cursor: pointer;
    }
    .rune-item.selected {
      border: 2px solid var(--rf-accent-primary, #e63946);
      background: #ffe3e3;
    }
    .rune-glyph {
      font-family: monospace;
      font-weight: 800;
      color: #2b2d42;
    }
    .rune-trans {
      font-style: italic;
      color: #2a9d8f;
    }
  `;

  @property({ type: String }) relicName = 'Amulet of the Sunken Spire';
  @property({ type: String }) relicType = 'amulet';
  @property({ type: String }) modelGeometry = 'amulet_sunken_spire';
  @property({ type: Array }) runes: RelicRune[] = [];
  @property({ type: Number }) metallic = 0.88;
  @property({ type: Number }) roughness = 0.22;
  @property({ type: String }) emissiveColor = '#00ffcc';

  @state() private rotX = 15;
  @state() private rotY = 45;
  @state() private zoom = 1.0;
  @state() private selectedRuneId: string | null = null;
  @state() private isDragging = false;
  private lastMouseX = 0;
  private lastMouseY = 0;

  @query('canvas') private canvasElement!: HTMLCanvasElement;

  firstUpdated() {
    this.drawRelic();
  }

  updated() {
    this.drawRelic();
  }

  private handleMouseDown(e: MouseEvent) {
    this.isDragging = true;
    this.lastMouseX = e.clientX;
    this.lastMouseY = e.clientY;
  }

  private handleMouseMove(e: MouseEvent) {
    if (!this.isDragging) return;
    const deltaX = e.clientX - this.lastMouseX;
    const deltaY = e.clientY - this.lastMouseY;
    this.rotY = (this.rotY + deltaX * 0.7) % 360;
    this.rotX = Math.max(-80, Math.min(80, this.rotX + deltaY * 0.7));
    this.lastMouseX = e.clientX;
    this.lastMouseY = e.clientY;
    this.drawRelic();
  }

  private handleMouseUp() {
    this.isDragging = false;
  }

  private drawRelic() {
    if (!this.canvasElement) return;
    const ctx = this.canvasElement.getContext('2d');
    if (!ctx) return;

    const width = (this.canvasElement.width = 480);
    const height = (this.canvasElement.height = 280);
    ctx.clearRect(0, 0, width, height);

    const centerX = width / 2;
    const centerY = height / 2;
    const radY = (this.rotY * Math.PI) / 180;
    const scale = this.zoom * (width / 5) * (0.8 + 0.2 * Math.cos(radY));

    // Draw ambient metallic sphere / relic medallion with lighting
    const grad = ctx.createRadialGradient(
      centerX - scale * 0.3,
      centerY - scale * 0.3,
      scale * 0.1,
      centerX,
      centerY,
      scale * 1.1
    );
    grad.addColorStop(0, '#f0f4f8');
    grad.addColorStop(0.3, '#718096');
    grad.addColorStop(0.8, '#1a202c');
    grad.addColorStop(1, '#0d1117');

    ctx.save();
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(centerX, centerY, scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = this.emissiveColor;
    ctx.stroke();

    // Emissive central gem
    const gemGrad = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, scale * 0.45);
    gemGrad.addColorStop(0, '#ffffff');
    gemGrad.addColorStop(0.4, this.emissiveColor);
    gemGrad.addColorStop(1, 'rgba(0, 255, 204, 0)');
    ctx.fillStyle = gemGrad;
    ctx.beginPath();
    ctx.arc(centerX, centerY, scale * 0.45, 0, Math.PI * 2);
    ctx.fill();

    // Engraved runic markers on outer perimeter
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px monospace';
    for (let i = 0; i < 8; i++) {
      const angle = (i * Math.PI) / 4 + radY;
      const rx = centerX + Math.cos(angle) * (scale * 0.75);
      const ry = centerY + Math.sin(angle) * (scale * 0.75);
      ctx.fillText('ᚱ', rx - 4, ry + 4);
    }
    ctx.restore();
  }

  private selectRune(rune: RelicRune) {
    this.selectedRuneId = rune.id;
    this.dispatchEvent(
      new CustomEvent('relic-rune-selected', {
        detail: { runeId: rune.id, inscription: rune.inscription, translated: rune.translated },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="header">
        <span class="title">${this.relicName}</span>
        <span class="badge">3D WebGL PBR</span>
      </div>

      <div
        class="viewport"
        @mousedown=${this.handleMouseDown}
        @mousemove=${this.handleMouseMove}
        @mouseup=${this.handleMouseUp}
        @mouseleave=${this.handleMouseUp}
      >
        <canvas></canvas>
        <div class="overlay-info">
          ROT: [${Math.round(this.rotX)}°, ${Math.round(this.rotY)}°] | METAL: ${this.metallic}
        </div>
      </div>

      <div class="controls">
        <button class="btn secondary" @click=${() => { this.rotX = 0; this.rotY = 0; }}>Reset View</button>
        <button class="btn" @click=${() => {
          this.dispatchEvent(new CustomEvent('relic-inspected', {
            detail: { relicName: this.relicName, rotX: this.rotX, rotY: this.rotY },
            bubbles: true,
            composed: true,
          }));
        }}>Log Inspection</button>
      </div>

      ${this.runes.length > 0
        ? html`
            <div class="runes-list">
              <div class="runes-title">Etched Runes & Inscriptions:</div>
              ${this.runes.map(
                (rune) => html`
                  <div
                    class="rune-item ${this.selectedRuneId === rune.id ? 'selected' : ''}"
                    @click=${() => this.selectRune(rune)}
                  >
                    <span class="rune-glyph">ᚱ ${rune.inscription}</span>
                    <span class="rune-trans">${rune.translated || 'Undeciphered'}</span>
                  </div>
                `
              )}
            </div>
          `
        : ''}
    `;
  }
}
