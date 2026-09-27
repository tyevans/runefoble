import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { westMarchesAtlasStyles } from './runefoble-west-marches-atlas.styles.ts';

export interface WestMarchesDiscovery {
  discovery_id: string;
  name: string;
  discovery_type: string;
  coordinates: { x: number; y: number };
  discovered_by_campaign_id: string;
  discovered_by_party_name: string;
  description?: string;
  danger_level?: number;
  timestamp?: string;
  notes?: string;
  is_private?: boolean;
  metadata?: Record<string, any>;
}

export interface WestMarchesOutpost {
  outpost_id: string;
  name: string;
  region: string;
  level: number;
  facilities: Record<string, number>;
  contributing_campaigns: string[];
  stored_resources?: Record<string, number>;
  boons?: string[];
  defensive_buffer?: number;
}

export interface WestMarchesNotice {
  notice_id: string;
  campaign_id: string;
  author_name: string;
  party_name?: string;
  title: string;
  content: string;
  notice_type: string;
  bounty_reward?: number | string;
  posted_at?: string;
}

const PARTY_COLORS: Record<string, string> = {
  'Party Blue': '#457b9d',
  'Party Gold': '#ffb703',
  'Nightstalkers': '#9b5de5',
  'Crimson Fangs': '#e63946',
};

@customElement('runefoble-west-marches-atlas')
export class RunefobleWestMarchesAtlas extends LitElement {
  static styles = westMarchesAtlasStyles;

  @property({ type: String }) sharedWorldId = '';
  @property({ type: String }) worldName = 'The Frontier Marches';
  @property({ type: String }) frontierRegion = 'The Untamed Wilds';
  @property({ type: String }) currentPartyId = '';
  @property({ type: String }) currentPartyName = 'Party Blue';
  @property({ type: String }) userRole = 'player';
  @property({ type: String }) activeTab: 'map' | 'stronghold' | 'tavern' | 'expeditions' = 'map';

  @property({ type: Array }) discoveries: WestMarchesDiscovery[] = [];
  @property({ type: Array }) outposts: WestMarchesOutpost[] = [];
  @property({ type: Array }) notices: WestMarchesNotice[] = [];

  @state() private selectedDiscovery: WestMarchesDiscovery | null = null;
  @state() private filterParty = 'all';
  @state() private filterType = 'all';
  @state() private minDanger = 0;
  @state() private noticeFilter = 'all';
  @state() private zoomLevel = 1.0;
  @state() private panX = 0;
  @state() private panY = 0;

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

  private handleCanvasClick(e: MouseEvent) {
    if (this.isDragging) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const rawX = Math.round((e.clientX - rect.left - this.panX) / this.zoomLevel);
    const rawY = Math.round((e.clientY - rect.top - this.panY) / this.zoomLevel);
    this.dispatchEvent(new CustomEvent('discovery-create-requested', {
      detail: { coordinates: { x: rawX, y: rawY }, sharedWorldId: this.sharedWorldId },
      bubbles: true,
      composed: true,
    }));
  }

  private selectDiscovery(d: WestMarchesDiscovery, e: Event) {
    e.stopPropagation();
    this.selectedDiscovery = d;
    this.dispatchEvent(new CustomEvent('pin-selected', {
      detail: { discovery: d, sharedWorldId: this.sharedWorldId },
      bubbles: true,
      composed: true,
    }));
  }

  private triggerUpgrade(outpostId: string, facilityId: string, currentTier: number) {
    this.dispatchEvent(new CustomEvent('stronghold-upgrade-requested', {
      detail: {
        outpost_id: outpostId,
        facility_id: facilityId,
        new_tier: currentTier + 1,
        sharedWorldId: this.sharedWorldId,
      },
      bubbles: true,
      composed: true,
    }));
  }

  private switchTab(tab: 'map' | 'stronghold' | 'tavern' | 'expeditions') {
    this.activeTab = tab;
    this.dispatchEvent(new CustomEvent('tab-changed', {
      detail: { tab },
      bubbles: true,
      composed: true,
    }));
  }

  private getPartyColor(partyName: string): string {
    return PARTY_COLORS[partyName] || '#2a9d8f';
  }

  private canViewPrivateNotes(d: WestMarchesDiscovery): boolean {
    if (this.userRole === 'guild_officer' || this.userRole === 'dm') return true;
    if (this.currentPartyId && d.discovered_by_campaign_id === this.currentPartyId) return true;
    if (this.currentPartyName && d.discovered_by_party_name === this.currentPartyName) return true;
    return !d.is_private;
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
            <button
              class="tab-btn ${this.activeTab === tab ? 'active' : ''}"
              @click=${() => this.switchTab(tab)}
            >
              ${tab === 'map' ? 'Frontier Map' : tab === 'stronghold' ? 'Communal Stronghold' : tab === 'tavern' ? 'Tavern Board' : 'Expedition Logs'}
            </button>
          `)}
        </div>
      </div>
      <div class="main-content">
        ${this.activeTab === 'map' ? this.renderMapView() : ''}
        ${this.activeTab === 'stronghold' ? this.renderStrongholdView() : ''}
        ${this.activeTab === 'tavern' ? this.renderTavernView() : ''}
        ${this.activeTab === 'expeditions' ? this.renderExpeditionsView() : ''}
      </div>
    `;
  }

  private renderMapView() {
    const parties = Array.from(new Set(this.discoveries.map((d) => d.discovered_by_party_name)));
    const visiblePins = this.discoveries.filter((d) => {
      if (this.filterParty !== 'all' && d.discovered_by_party_name !== this.filterParty) return false;
      if (this.filterType !== 'all' && d.discovery_type !== this.filterType) return false;
      return !(this.minDanger > 0 && (d.danger_level || 1) < this.minDanger);
    });

    return html`
      <div
        class="map-wrapper"
        @mousedown=${this.handleMouseDown}
        @mousemove=${this.handleMouseMove}
        @mouseup=${() => { this.isDragging = false; }}
        @mouseleave=${() => { this.isDragging = false; }}
        @click=${this.handleCanvasClick}
      >
        <div class="filter-panel">
          <label>Party:</label>
          <select class="filter-select" .value=${this.filterParty} @change=${(e: Event) => (this.filterParty = (e.target as HTMLSelectElement).value)}>
            <option value="all">All Parties</option>
            ${parties.map((p) => html`<option value=${p}>${p}</option>`)}
          </select>
          <label>Type:</label>
          <select class="filter-select" .value=${this.filterType} @change=${(e: Event) => (this.filterType = (e.target as HTMLSelectElement).value)}>
            <option value="all">All Types</option>
            <option value="dungeon">Dungeon</option>
            <option value="outpost">Outpost</option>
            <option value="ruin">Ruin</option>
            <option value="waypoint">Waypoint</option>
            <option value="hazard">Hazard</option>
          </select>
          <label>Min Danger:</label>
          <select class="filter-select" .value=${String(this.minDanger)} @change=${(e: Event) => (this.minDanger = Number((e.target as HTMLSelectElement).value))}>
            <option value="0">All</option>
            <option value="2">Lv 2+</option>
            <option value="3">Lv 3+</option>
            <option value="4">Lv 4+</option>
          </select>
        </div>
        <svg class="map-svg" viewBox="0 0 1000 1000">
          <g transform="translate(${this.panX}, ${this.panY}) scale(${this.zoomLevel})">
            <defs>
              <pattern id="west-marches-grid" width="50" height="50" patternUnits="userSpaceOnUse">
                <path d="M 50 0 L 0 0 0 50" fill="none" class="frontier-grid" />
              </pattern>
            </defs>
            <rect width="1000" height="1000" fill="url(#west-marches-grid)" />
            ${this.outposts.map((outpost, i) => html`
              <g class="outpost-marker" transform="translate(${200 + i * 350}, ${300 + (i % 2) * 200})">
                <rect x="-18" y="-18" width="36" height="36" class="outpost-circle" />
                <text x="0" y="28" text-anchor="middle" class="pin-tag">🏰 ${outpost.name}</text>
              </g>
            `)}
            ${visiblePins.map((d) => {
              const color = this.getPartyColor(d.discovered_by_party_name);
              const isSelected = this.selectedDiscovery?.discovery_id === d.discovery_id;
              return html`
                <g class="pin-marker" transform="translate(${d.coordinates.x}, ${d.coordinates.y})" @click=${(e: Event) => this.selectDiscovery(d, e)}>
                  <circle r=${isSelected ? 14 : 9} class="pin-circle" style="fill: ${color}; stroke-width: ${isSelected ? 3 : 2}px;" />
                  <text y="3" class="pin-danger">${d.danger_level || 1}</text>
                  <text x="14" y="4" class="pin-tag">${d.name}</text>
                </g>
              `;
            })}
          </g>
        </svg>
        <div class="map-controls">
          <button class="map-btn" @click=${() => (this.zoomLevel = Math.min(3.0, this.zoomLevel + 0.25))}>+</button>
          <button class="map-btn" @click=${() => (this.zoomLevel = Math.max(0.5, this.zoomLevel - 0.25))}>-</button>
          <button class="map-btn" @click=${() => { this.zoomLevel = 1.0; this.panX = 0; this.panY = 0; }}>⟲</button>
        </div>
        ${this.selectedDiscovery ? this.renderInspectionPopover(this.selectedDiscovery) : ''}
      </div>
    `;
  }

  private renderInspectionPopover(d: WestMarchesDiscovery) {
    const canSeeNotes = this.canViewPrivateNotes(d);
    return html`
      <div class="inspection-popover">
        <div class="popover-header">
          <h4 class="popover-title">${d.name}</h4>
          <button class="popover-close" @click=${() => (this.selectedDiscovery = null)}>×</button>
        </div>
        <div class="badge-row">
          <span class="type-badge">${d.discovery_type}</span>
          <span class="danger-badge">💀 Danger Lv ${d.danger_level || 1}</span>
          <span class="attribution-badge" style="background: ${this.getPartyColor(d.discovered_by_party_name)}">
            ${d.discovered_by_party_name}
          </span>
        </div>
        <div class="popover-desc">${d.description || 'No detailed description recorded.'}</div>
        ${d.notes ? html`
          ${canSeeNotes
            ? html`<div class="popover-notes"><strong>Expedition Notes:</strong> ${d.notes}</div>`
            : html`<div class="zanzibar-notice">🔒 SpiceDB Protected: Private notes restricted to ${d.discovered_by_party_name}</div>`
          }
        ` : ''}
        <div style="font-size: 0.68rem; color: #888;">
          Coordinates: (${d.coordinates.x}, ${d.coordinates.y}) ${d.timestamp ? `• ${d.timestamp.slice(0, 10)}` : ''}
        </div>
      </div>
    `;
  }

  private renderStrongholdView() {
    const outpost = this.outposts[0] || {
      outpost_id: 'default',
      name: 'Communal Frontier Stronghold',
      region: this.frontierRegion,
      level: 1,
      facilities: { alchemical_workshop: 1, watchtower: 1, trading_post: 1 },
      contributing_campaigns: ['Party Blue', 'Party Gold'],
      boons: ['Reagent Extraction (+1 Herbal Reagent)', 'Early Warning (+1 Initiative)'],
      defensive_buffer: 15,
      stored_resources: { gold: 120, timber: 25 },
    };

    return html`
      <div class="stronghold-view">
        <div class="dashboard-banner">
          <div class="banner-text">
            <h3>🏰 ${outpost.name}</h3>
            <div class="banner-meta">
              Region: ${outpost.region} • Defense: +${outpost.defensive_buffer || 10} AC •
              Contributing: ${outpost.contributing_campaigns.join(', ')}
            </div>
          </div>
        </div>
        <div class="facility-grid">
          ${Object.entries(outpost.facilities).map(([facId, tier]) => {
            const facTitle = facId.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
            return html`
              <div class="facility-card">
                <div class="facility-header">
                  <span class="facility-title">${facTitle}</span>
                  <span class="facility-tier-badge">Tier ${tier}</span>
                </div>
                <div><strong>Shared Boons:</strong></div>
                <ul class="boons-list">
                  ${(outpost.boons || []).filter((b) => b.toLowerCase().includes(facId.split('_')[0])).map((boon) => html`<li>${boon}</li>`)}
                  ${(outpost.boons || []).filter((b) => b.toLowerCase().includes(facId.split('_')[0])).length === 0
                    ? html`<li>Active baseline facility bonus (Lv ${tier})</li>`
                    : ''}
                </ul>
                <button class="upgrade-btn" @click=${() => this.triggerUpgrade(outpost.outpost_id, facId, tier)}>
                  Upgrade Facility (Lv ${tier + 1})
                </button>
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }

  private renderTavernView() {
    const visibleNotices = this.notices.filter((n) => this.noticeFilter === 'all' || n.notice_type === this.noticeFilter);
    return html`
      <div class="tavern-view">
        <div class="tavern-controls">
          <div style="font-weight: 800; font-size: 1.1rem;">🍺 The Communal Tavern Notice Board</div>
          <select class="filter-select" .value=${this.noticeFilter} @change=${(e: Event) => (this.noticeFilter = (e.target as HTMLSelectElement).value)}>
            <option value="all">All Notices</option>
            <option value="bounty">Bounties</option>
            <option value="rumor">Rumors</option>
            <option value="request">Expedition Requests</option>
          </select>
        </div>
        <div class="notice-grid">
          ${visibleNotices.map((n) => html`
            <div class="notice-card">
              <span class="notice-type-tag ${n.notice_type}">${n.notice_type}</span>
              <h4 class="notice-title">${n.title}</h4>
              <div class="notice-body">${n.content}</div>
              ${n.bounty_reward ? html`<div class="bounty-reward">🪙 Bounty: ${n.bounty_reward} Gold</div>` : ''}
              <div class="notice-meta">Posted by ${n.author_name} ${n.party_name ? `(${n.party_name})` : ''}</div>
            </div>
          `)}
        </div>
      </div>
    `;
  }

  private renderExpeditionsView() {
    return html`
      <div class="expeditions-view">
        <div style="font-weight: 800; font-size: 1.1rem;">🧭 Cross-Campaign Expedition Chronicle</div>
        <table class="log-table">
          <thead>
            <tr><th>Discovery</th><th>Type</th><th>Party</th><th>Danger</th><th>Coordinates</th><th>Date</th></tr>
          </thead>
          <tbody>
            ${this.discoveries.map((d) => html`
              <tr>
                <td><strong>${d.name}</strong></td>
                <td><span class="type-badge">${d.discovery_type}</span></td>
                <td><span class="attribution-badge" style="background: ${this.getPartyColor(d.discovered_by_party_name)}">${d.discovered_by_party_name}</span></td>
                <td>💀 Lv ${d.danger_level || 1}</td>
                <td>(${d.coordinates.x}, ${d.coordinates.y})</td>
                <td>${d.timestamp ? d.timestamp.slice(0, 10) : 'Recent'}</td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }
}
