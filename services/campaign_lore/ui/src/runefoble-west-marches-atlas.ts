import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { westMarchesAtlasStyles } from './runefoble-west-marches-atlas.styles.ts';
import './west_marches/index.ts';
import { snapToHexGrid } from './west_marches/frontier_hex_overlay.ts';
import type { WestMarchesDiscovery, WestMarchesNotice, WestMarchesOutpost } from './west_marches/types.ts';

export * from './west_marches/types.ts';

@customElement('runefoble-west-marches-atlas')
export class RunefobleWestMarchesAtlas extends LitElement {
  static styles = westMarchesAtlasStyles;

  @property({ type: String }) sharedWorldId = '';
  @property({ type: String }) worldName = 'The Frontier Marches';
  @property({ type: String }) frontierRegion = 'The Untamed Wilds';
  @property({ type: String }) currentPartyId = ''; @property({ type: String }) currentPartyName = 'Party Blue';
  @property({ type: String }) userRole = 'player';
  @property({ type: String }) activeTab: 'map' | 'stronghold' | 'tavern' | 'expeditions' = 'map';
  @property({ type: Array }) discoveries: WestMarchesDiscovery[] = [];
  @property({ type: Array }) outposts: WestMarchesOutpost[] = []; @property({ type: Array }) notices: WestMarchesNotice[] = [];

  @state() private selectedDiscovery: WestMarchesDiscovery | null = null;
  @state() private filterParty = 'all'; @state() private filterType = 'all';
  @state() private minDanger = 0; @state() private zoomLevel = 1.0;
  @state() private panX = 0; @state() private panY = 0;

  private isDragging = false; private startX = 0; private startY = 0;

  private handleMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).tagName.toLowerCase() === 'circle') return;
    this.isDragging = true; this.startX = e.clientX - this.panX; this.startY = e.clientY - this.panY;
  }

  private handleMouseMove(e: MouseEvent) {
    if (!this.isDragging) return;
    this.panX = e.clientX - this.startX; this.panY = e.clientY - this.startY;
  }

  private handleCanvasClick(e: MouseEvent) {
    if (this.isDragging) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const rawX = Math.round((e.clientX - rect.left - this.panX) / this.zoomLevel);
    const rawY = Math.round((e.clientY - rect.top - this.panY) / this.zoomLevel);
    this.dispatchEvent(new CustomEvent('discovery-create-requested', {
      detail: { coordinates: snapToHexGrid(rawX, rawY), sharedWorldId: this.sharedWorldId }, bubbles: true, composed: true,
    }));
  }

  private switchTab(tab: 'map' | 'stronghold' | 'tavern' | 'expeditions') {
    this.activeTab = tab;
    this.dispatchEvent(new CustomEvent('tab-changed', { detail: { tab }, bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="top-bar">
        <div class="title-group">
          <span class="title">🗺️ ${this.worldName}</span>
          <span class="region-badge">${this.frontierRegion}</span>
          <span class="party-badge">${this.currentPartyName}</span>
          <span class="role-badge">${this.userRole}</span>
        </div>
        <div class="nav-tabs">
          ${(['map', 'stronghold', 'tavern', 'expeditions'] as const).map(tab => html`
            <button class="tab-btn ${this.activeTab === tab ? 'active' : ''}" @click=${() => this.switchTab(tab)}>
              ${tab === 'map' ? 'Frontier Map' : tab === 'stronghold' ? 'Communal Stronghold' : tab === 'tavern' ? 'Tavern Board' : 'Expedition Logs'}
            </button>
          `)}
        </div>
      </div>
      <div class="main-content">
        ${this.activeTab === 'map' ? this.renderMapView() : ''}
        ${this.activeTab === 'stronghold' ? html`<runefoble-stronghold-dashboard-panel .outposts=${this.outposts} .frontierRegion=${this.frontierRegion} .sharedWorldId=${this.sharedWorldId}></runefoble-stronghold-dashboard-panel>` : ''}
        ${this.activeTab === 'tavern' ? html`<runefoble-tavern-notice-board .notices=${this.notices}></runefoble-tavern-notice-board>` : ''}
        ${this.activeTab === 'expeditions' ? html`<runefoble-expedition-chronicle .discoveries=${this.discoveries}></runefoble-expedition-chronicle>` : ''}
      </div>
    `;
  }

  private renderMapView() {
    const parties = Array.from(new Set(this.discoveries.map((d) => d.discovered_by_party_name)));
    return html`
      <div class="map-wrapper" @mousedown=${this.handleMouseDown} @mousemove=${this.handleMouseMove}
        @mouseup=${() => { this.isDragging = false; }} @mouseleave=${() => { this.isDragging = false; }} @click=${this.handleCanvasClick}>
        <div class="filter-panel" @click=${(e: Event) => e.stopPropagation()}>
          <label>Party:</label>
          <select class="filter-select" .value=${this.filterParty} @change=${(e: Event) => (this.filterParty = (e.target as HTMLSelectElement).value)}>
            <option value="all">All Parties</option>${parties.map((p) => html`<option value=${p}>${p}</option>`)}
          </select>
          <label>Type:</label>
          <select class="filter-select" .value=${this.filterType} @change=${(e: Event) => (this.filterType = (e.target as HTMLSelectElement).value)}>
            <option value="all">All Types</option><option value="dungeon">Dungeon</option><option value="outpost">Outpost</option><option value="ruin">Ruin</option><option value="waypoint">Waypoint</option><option value="hazard">Hazard</option>
          </select>
          <label>Min Danger:</label>
          <select class="filter-select" .value=${String(this.minDanger)} @change=${(e: Event) => (this.minDanger = Number((e.target as HTMLSelectElement).value))}>
            <option value="0">All</option><option value="2">Lv 2+</option><option value="3">Lv 3+</option><option value="4">Lv 4+</option>
          </select>
        </div>
        <runefoble-frontier-hex-overlay .panX=${this.panX} .panY=${this.panY} .zoomLevel=${this.zoomLevel}></runefoble-frontier-hex-overlay>
        <runefoble-discovery-pin-layer
          .discoveries=${this.discoveries} .outposts=${this.outposts}
          .selectedDiscovery=${this.selectedDiscovery} .filterParty=${this.filterParty}
          .filterType=${this.filterType} .minDanger=${this.minDanger}
          .currentPartyId=${this.currentPartyId} .currentPartyName=${this.currentPartyName}
          .userRole=${this.userRole} .sharedWorldId=${this.sharedWorldId}
          .panX=${this.panX} .panY=${this.panY} .zoomLevel=${this.zoomLevel}
          @pin-selected=${(e: CustomEvent) => { this.selectedDiscovery = e.detail.discovery; }}
          @pin-deselected=${() => { this.selectedDiscovery = null; }}
        ></runefoble-discovery-pin-layer>
        <div class="map-controls" @click=${(e: Event) => e.stopPropagation()}>
          <button class="map-btn" @click=${() => (this.zoomLevel = Math.min(3.0, this.zoomLevel + 0.25))}>+</button>
          <button class="map-btn" @click=${() => (this.zoomLevel = Math.max(0.5, this.zoomLevel - 0.25))}>-</button>
          <button class="map-btn" @click=${() => { this.zoomLevel = 1.0; this.panX = 0; this.panY = 0; }}>⟲</button>
        </div>
      </div>
    `;
  }
}
