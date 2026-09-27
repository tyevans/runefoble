import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { atlasStyles } from './runefoble-campaign-atlas.styles.ts';

export interface AtlasPin {
  pin_id: string;
  title: string;
  layer: string;
  coordinates: { x: number; y: number };
  description?: string;
  era?: string;
  session_id?: string;
  linked_entity_ids?: string[];
  metadata?: Record<string, any>;
}

export interface AtlasTerritory {
  territory_id: string;
  name: string;
  layer: string;
  polygon_coordinates: number[][];
  owner_faction: string;
  is_contested: boolean;
  era?: string;
  metadata?: Record<string, any>;
}

export interface CodexEntry {
  entry_id: string;
  title: string;
  content: string;
  illuminated_content?: string;
  privacy: 'private' | 'party_shared' | 'public';
  author_id: string;
  era?: string;
  tags?: string[];
  linked_entities?: Array<{ id: string; name: string; entity_type: string }>;
}

@customElement('runefoble-campaign-atlas')
export class RunefobleCampaignAtlas extends LitElement {
  static styles = atlasStyles;


  @property({ type: String })
  campaignId = '';

  @property({ type: String })
  activeLayer = 'continental';

  @property({ type: String })
  activeEra = '';

  @property({ type: Array })
  pins: AtlasPin[] = [];

  @property({ type: Array })
  territories: AtlasTerritory[] = [];

  @property({ type: Array })
  codexEntries: CodexEntry[] = [];

  @property({ type: Boolean })
  isDM = false;

  @state()
  private zoomLevel = 1.0;

  @state()
  private panX = 0;

  @state()
  private panY = 0;

  @state()
  private selectedPin: AtlasPin | null = null;

  @state()
  private selectedEntry: CodexEntry | null = null;

  @state()
  private showContestedOnly = false;

  private isDragging = false;
  private startX = 0;
  private startY = 0;

  private handleMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).tagName.toLowerCase() === 'circle') return;
    this.isDragging = true;
    this.startX = e.clientX - this.panX;
    this.startY = e.clientY - this.panY;
  }

  private handleMouseMove(e: MouseEvent) {
    if (!this.isDragging) return;
    this.panX = e.clientX - this.startX;
    this.panY = e.clientY - this.startY;
  }

  private handleMouseUp() {
    this.isDragging = false;
  }

  private zoomIn() {
    this.zoomLevel = Math.min(3.0, this.zoomLevel + 0.25);
  }

  private zoomOut() {
    this.zoomLevel = Math.max(0.5, this.zoomLevel - 0.25);
  }

  private resetView() {
    this.zoomLevel = 1.0;
    this.panX = 0;
    this.panY = 0;
  }

  private selectLayer(layer: string) {
    this.activeLayer = layer;
    this.dispatchEvent(
      new CustomEvent('layer-change', {
        detail: { layer, campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handlePinClick(pin: AtlasPin, e: Event) {
    e.stopPropagation();
    this.selectedPin = pin;
    this.dispatchEvent(
      new CustomEvent('pin-selected', {
        detail: { pin, campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleCanvasClick(e: MouseEvent) {
    if (this.isDragging) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const rawX = (e.clientX - rect.left - this.panX) / this.zoomLevel;
    const rawY = (e.clientY - rect.top - this.panY) / this.zoomLevel;

    this.dispatchEvent(
      new CustomEvent('pin-create-requested', {
        detail: {
          coordinates: { x: Math.round(rawX), y: Math.round(rawY) },
          layer: this.activeLayer,
          campaignId: this.campaignId,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const visiblePins = this.pins.filter((pin) => {
      if (this.activeEra && pin.era && !pin.era.toLowerCase().includes(this.activeEra.toLowerCase())) {
        return false;
      }
      return pin.layer === this.activeLayer || pin.layer === 'continental';
    });

    const visibleTerritories = this.territories.filter((t) => {
      if (this.showContestedOnly && !t.is_contested) return false;
      if (this.activeEra && t.era && !t.era.toLowerCase().includes(this.activeEra.toLowerCase())) {
        return false;
      }
      return t.layer === this.activeLayer || t.layer === 'continental';
    });

    return html`
      <div class="top-bar">
        <div class="title-group">
          <span class="title">Campaign World Atlas & Codex</span>
          <span class="layer-badge">${this.activeLayer} layer</span>
          ${this.activeEra ? html`<span class="layer-badge" style="background:#a8dadc;">${this.activeEra}</span>` : ''}
        </div>
        <div class="btn-group">
          <button
            class="btn ${this.showContestedOnly ? 'active' : ''}"
            @click=${() => (this.showContestedOnly = !this.showContestedOnly)}
          >
            Contested Borders
          </button>
          <button class="btn" @click=${this.resetView}>Reset View</button>
        </div>
      </div>

      <div class="main-viewport">
        <div
          class="canvas-container"
          @mousedown=${this.handleMouseDown}
          @mousemove=${this.handleMouseMove}
          @mouseup=${this.handleMouseUp}
          @mouseleave=${this.handleMouseUp}
          @click=${this.handleCanvasClick}
        >
          <svg class="map-svg" viewBox="0 0 1000 1000">
            <g transform="translate(${this.panX}, ${this.panY}) scale(${this.zoomLevel})">
              <!-- Grid background -->
              <defs>
                <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                  <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e0e0e0" stroke-width="1" />
                </pattern>
              </defs>
              <rect width="1000" height="1000" fill="url(#grid)" />

              <!-- Geopolitical Territories -->
              ${visibleTerritories.map((t) => {
                const points = t.polygon_coordinates.map((p) => `${p[0]},${p[1]}`).join(' ');
                const fill = t.metadata?.banner_color || '#457b9d';
                return html`
                  <polygon
                    points=${points}
                    class="territory-poly ${t.is_contested ? 'contested' : ''}"
                    style="fill: ${fill};"
                  />
                `;
              })}

              <!-- Milestone Pins -->
              ${visiblePins.map((pin) => {
                const isSelected = this.selectedPin?.pin_id === pin.pin_id;
                return html`
                  <g
                    class="pin-marker"
                    transform="translate(${pin.coordinates.x}, ${pin.coordinates.y})"
                    @click=${(e: Event) => this.handlePinClick(pin, e)}
                  >
                    <circle
                      r=${isSelected ? 10 : 7}
                      class="pin-dot"
                      style="fill: ${isSelected ? '#ffb703' : '#e63946'};"
                    />
                    <text x="12" y="4" class="pin-label">${pin.title}</text>
                  </g>
                `;
              })}
            </g>
          </svg>

          <div class="zoom-controls">
            <button class="zoom-btn" @click=${this.zoomIn}>+</button>
            <button class="zoom-btn" @click=${this.zoomOut}>-</button>
          </div>
        </div>

        <!-- Sidebar: Layers & Living Codex -->
        <div class="drawer">
          <div class="drawer-header">
            <span>Layers & Codex</span>
            <span style="font-size: 0.75rem; color: #666;">${this.codexEntries.length} notes</span>
          </div>

          <div class="drawer-content">
            <div class="filter-group">
              <span class="filter-label">Zoom Layer</span>
              <div class="layer-selector">
                <button
                  class="layer-btn ${this.activeLayer === 'continental' ? 'selected' : ''}"
                  @click=${() => this.selectLayer('continental')}
                >
                  Continental
                </button>
                <button
                  class="layer-btn ${this.activeLayer === 'regional' ? 'selected' : ''}"
                  @click=${() => this.selectLayer('regional')}
                >
                  Regional
                </button>
                <button
                  class="layer-btn ${this.activeLayer === 'municipal' ? 'selected' : ''}"
                  @click=${() => this.selectLayer('municipal')}
                >
                  Municipal
                </button>
              </div>
            </div>

            <div class="filter-group">
              <span class="filter-label">Chronological Era</span>
              <input
                type="text"
                class="era-input"
                placeholder="Filter era / session..."
                .value=${this.activeEra}
                @input=${(e: Event) => (this.activeEra = (e.target as HTMLInputElement).value)}
              />
            </div>

            <div class="filter-group">
              <span class="filter-label">Collaborative Codex</span>
              ${this.codexEntries.map(
                (entry) => html`
                  <div
                    class="codex-card ${this.selectedEntry?.entry_id === entry.entry_id ? 'selected' : ''}"
                    @click=${() => (this.selectedEntry = entry)}
                  >
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                      <strong style="font-size: 0.85rem;">${entry.title}</strong>
                      <span class="privacy-tag ${entry.privacy}">${entry.privacy.replace('_', ' ')}</span>
                    </div>
                    <div class="entry-body">
                      ${entry.content.length > 80 ? entry.content.slice(0, 80) + '...' : entry.content}
                    </div>
                    ${entry.linked_entities && entry.linked_entities.length > 0
                      ? html`
                          <div style="margin-top: 4px;">
                            ${entry.linked_entities.map(
                              (ent) => html`<span class="entity-tag">${ent.name}</span>`
                            )}
                          </div>
                        `
                      : ''}
                  </div>
                `
              )}
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
