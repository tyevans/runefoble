import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { mapUploaderStyles } from './runefoble-map-uploader.styles.ts';

export interface GridConfigDetail {
  gridCols: number;
  gridRows: number;
  gridOpacity: number;
  shroudOpacity: number;
  shroudEnabled: boolean;
  revealedCells: Set<string>;
}

@customElement('runefoble-map-grid-config')
export class RunefobleMapGridConfig extends LitElement {
  static styles = mapUploaderStyles;

  @property({ type: String }) previewUrl: string | null = null;
  @property({ type: Number }) gridCols = 10;
  @property({ type: Number }) gridRows = 10;
  @property({ type: Number }) gridOpacity = 0.5;
  @property({ type: Number }) shroudOpacity = 0.75;
  @property({ type: Boolean }) shroudEnabled = true;
  @property({ type: Object }) revealedCells: Set<string> = new Set();

  private emitChange() {
    this.dispatchEvent(new CustomEvent<GridConfigDetail>('grid-change', {
      bubbles: true, composed: true,
      detail: {
        gridCols: this.gridCols, gridRows: this.gridRows, gridOpacity: this.gridOpacity,
        shroudOpacity: this.shroudOpacity, shroudEnabled: this.shroudEnabled,
        revealedCells: this.revealedCells,
      },
    }));
  }

  toggleCellShroud(x: number, y: number) {
    const key = `${x},${y}`;
    const next = new Set(this.revealedCells);
    if (next.has(key)) next.delete(key); else next.add(key);
    this.revealedCells = next;
    this.emitChange();
  }

  revealAll() {
    const all = new Set<string>();
    for (let y = 0; y < this.gridRows; y++) {
      for (let x = 0; x < this.gridCols; x++) all.add(`${x},${y}`);
    }
    this.revealedCells = all;
    this.emitChange();
  }

  shroudAll() {
    this.revealedCells = new Set();
    this.emitChange();
  }

  render() {
    return html`
      <div class="preview-container">
        ${this.previewUrl ? html`<img src="${this.previewUrl}" alt="Tactical Battlemap" class="preview-image" />` : ''}
        <div
          class="shroud-overlay"
          style="grid-template-columns: repeat(${this.gridCols}, 1fr); grid-template-rows: repeat(${this.gridRows}, 1fr); opacity: ${this.shroudEnabled ? this.shroudOpacity : 0};"
        >
          ${Array.from({ length: this.gridCols * this.gridRows }).map((_, idx) => {
            const x = idx % this.gridCols;
            const y = Math.floor(idx / this.gridCols);
            const isRevealed = this.revealedCells.has(`${x},${y}`);
            return html`
              <div
                class="shroud-cell ${isRevealed ? 'revealed' : 'shrouded'}"
                @click="${() => this.toggleCellShroud(x, y)}"
                title="Cell (${x}, ${y}) - Click to toggle shroud"
              ></div>
            `;
          })}
        </div>
      </div>

      <div class="controls-panel">
        <div class="slider-group">
          <label><span>Grid Columns</span><span>${this.gridCols}</span></label>
          <input
            type="range" min="4" max="32" .value="${String(this.gridCols)}"
            @input="${(e: Event) => { this.gridCols = Number((e.target as HTMLInputElement).value); this.emitChange(); }}"
          />
        </div>
        <div class="slider-group">
          <label><span>Grid Rows</span><span>${this.gridRows}</span></label>
          <input
            type="range" min="4" max="32" .value="${String(this.gridRows)}"
            @input="${(e: Event) => { this.gridRows = Number((e.target as HTMLInputElement).value); this.emitChange(); }}"
          />
        </div>
        <div class="slider-group">
          <label><span>Shroud Opacity</span><span>${Math.round(this.shroudOpacity * 100)}%</span></label>
          <input
            type="range" min="0" max="1" step="0.05" .value="${String(this.shroudOpacity)}"
            @input="${(e: Event) => { this.shroudOpacity = Number((e.target as HTMLInputElement).value); this.emitChange(); }}"
          />
        </div>
        <div style="display: flex; gap: 8px; align-items: flex-end; flex-wrap: wrap;">
          <button
            class="btn ${this.shroudEnabled ? 'btn-primary' : ''}"
            @click="${() => { this.shroudEnabled = !this.shroudEnabled; this.emitChange(); }}"
          >
            Shroud: ${this.shroudEnabled ? 'ON' : 'OFF'}
          </button>
          <button class="btn" @click="${this.revealAll}">Reveal All</button>
          <button class="btn" @click="${this.shroudAll}">Shroud All</button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-map-grid-config': RunefobleMapGridConfig;
  }
}
