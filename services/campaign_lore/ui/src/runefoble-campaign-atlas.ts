import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { atlasStyles } from './runefoble-campaign-atlas.styles.ts';
import {
  type AtlasPin, type AtlasTerritory, type CodexEntry,
  renderTerritories, renderTerritoryDefs, renderPinsLayer,
  calculateCanvasCoordinates, renderCodexSidebar,
} from './atlas/index.ts';

export type { AtlasPin, AtlasTerritory, CodexEntry };

@customElement('runefoble-campaign-atlas')
export class RunefobleCampaignAtlas extends LitElement {
  static styles = atlasStyles;

  @property({ type: String }) campaignId = '';
  @property({ type: String }) activeLayer = 'continental';
  @property({ type: String }) activeEra = '';
  @property({ type: Array }) pins: AtlasPin[] = [];
  @property({ type: Array }) territories: AtlasTerritory[] = [];
  @property({ type: Array }) codexEntries: CodexEntry[] = [];
  @property({ type: Boolean }) isDM = false;

  @state() private zoomLevel = 1.0;
  @state() private panX = 0;
  @state() private panY = 0;
  @state() private selectedPin: AtlasPin | null = null;
  @state() private selectedEntry: CodexEntry | null = null;
  @state() private showContestedOnly = false;

  private isDragging = false;
  private startX = 0;
  private startY = 0;

  private handleMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).tagName?.toLowerCase() === 'circle') return;
    this.isDragging = true;
    this.startX = e.clientX - this.panX; this.startY = e.clientY - this.panY;
  }
  private handleMouseMove(e: MouseEvent) {
    if (!this.isDragging) return;
    this.panX = e.clientX - this.startX; this.panY = e.clientY - this.startY;
  }
  private handleMouseUp() { this.isDragging = false; }
  private zoomIn() { this.zoomLevel = Math.min(3.0, this.zoomLevel + 0.25); }
  private zoomOut() { this.zoomLevel = Math.max(0.5, this.zoomLevel - 0.25); }
  private resetView() { this.zoomLevel = 1.0; this.panX = 0; this.panY = 0; }

  private emit(name: string, detail: Record<string, unknown>) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }
  private selectLayer(layer: string) {
    this.activeLayer = layer;
    this.emit('layer-change', { layer, campaignId: this.campaignId });
  }
  private handlePinClick(pin: AtlasPin, e: Event) {
    e.stopPropagation();
    this.selectedPin = pin;
    this.emit('pin-selected', { pin, campaignId: this.campaignId });
  }
  private handleCanvasClick(e: MouseEvent) {
    if (this.isDragging) return;
    const coordinates = calculateCanvasCoordinates(e, this.panX, this.panY, this.zoomLevel);
    this.emit('pin-create-requested', { coordinates, layer: this.activeLayer, campaignId: this.campaignId });
  }

  render() {
    return html`
      <div class="top-bar">
        <div class="title-group">
          <span class="title">Campaign World Atlas & Codex</span>
          <span class="layer-badge">${this.activeLayer} layer</span>
          ${this.activeEra ? html`<span class="layer-badge" style="background:#a8dadc;">${this.activeEra}</span>` : ''}
        </div>
        <div class="btn-group">
          <button class="btn ${this.showContestedOnly ? 'active' : ''}" @click=${() => (this.showContestedOnly = !this.showContestedOnly)}>
            Contested Borders
          </button>
          <button class="btn" @click=${this.resetView}>Reset View</button>
        </div>
      </div>
      <div class="main-viewport">
        <div class="canvas-container" @mousedown=${this.handleMouseDown} @mousemove=${this.handleMouseMove} @mouseup=${this.handleMouseUp} @mouseleave=${this.handleMouseUp} @click=${this.handleCanvasClick}>
          <svg class="map-svg" viewBox="0 0 1000 1000">
            <g transform="translate(${this.panX}, ${this.panY}) scale(${this.zoomLevel})">
              <defs>
                <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                  <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e0e0e0" stroke-width="1" />
                </pattern>
                ${renderTerritoryDefs()}
              </defs>
              <rect width="1000" height="1000" fill="url(#grid)" />
              ${renderTerritories({ territories: this.territories, activeLayer: this.activeLayer, activeEra: this.activeEra, showContestedOnly: this.showContestedOnly })}
              ${renderPinsLayer({ pins: this.pins, activeLayer: this.activeLayer, activeEra: this.activeEra, selectedPinId: this.selectedPin?.pin_id, onPinClick: (p, ev) => this.handlePinClick(p, ev) })}
            </g>
          </svg>
          <div class="zoom-controls">
            <button class="zoom-btn" @click=${this.zoomIn}>+</button>
            <button class="zoom-btn" @click=${this.zoomOut}>-</button>
          </div>
        </div>
        ${renderCodexSidebar({
          codexEntries: this.codexEntries, activeLayer: this.activeLayer, activeEra: this.activeEra,
          selectedEntryId: this.selectedEntry?.entry_id, onSelectLayer: (l) => this.selectLayer(l),
          onEraInput: (era) => (this.activeEra = era), onSelectEntry: (entry) => (this.selectedEntry = entry),
        })}
      </div>
    `;
  }
}
