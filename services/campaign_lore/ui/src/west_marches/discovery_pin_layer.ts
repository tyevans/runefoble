import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { pinStyles } from './styles/pin.styles.ts';
import { type WestMarchesDiscovery, type WestMarchesOutpost, PARTY_COLORS } from './types.ts';

@customElement('runefoble-discovery-pin-layer')
export class RunefobleDiscoveryPinLayer extends LitElement {
  static styles = pinStyles;

  @property({ type: Array }) discoveries: WestMarchesDiscovery[] = [];
  @property({ type: Array }) outposts: WestMarchesOutpost[] = [];
  @property({ type: Object }) selectedDiscovery: WestMarchesDiscovery | null = null;
  @property({ type: String }) filterParty = 'all';
  @property({ type: String }) filterType = 'all';
  @property({ type: Number }) minDanger = 0;
  @property({ type: String }) currentPartyId = '';
  @property({ type: String }) currentPartyName = 'Party Blue';
  @property({ type: String }) userRole = 'player';
  @property({ type: String }) sharedWorldId = '';
  @property({ type: Number }) panX = 0;
  @property({ type: Number }) panY = 0;
  @property({ type: Number }) zoomLevel = 1.0;

  private getPartyColor(name: string): string {
    return PARTY_COLORS[name] || '#2a9d8f';
  }

  public canViewPrivateNotes(d: WestMarchesDiscovery): boolean {
    if (this.userRole === 'guild_officer' || this.userRole === 'dm') return true;
    if (this.currentPartyId && d.discovered_by_campaign_id === this.currentPartyId) return true;
    if (this.currentPartyName && d.discovered_by_party_name === this.currentPartyName) return true;
    return !d.is_private;
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

  private closePopover() {
    this.selectedDiscovery = null;
    this.dispatchEvent(new CustomEvent('pin-deselected', { bubbles: true, composed: true }));
  }

  render() {
    const visiblePins = this.discoveries.filter((d) => {
      if (this.filterParty !== 'all' && d.discovered_by_party_name !== this.filterParty) return false;
      if (this.filterType !== 'all' && d.discovery_type !== this.filterType) return false;
      return !(this.minDanger > 0 && (d.danger_level || 1) < this.minDanger);
    });

    return html`
      <svg class="pins-svg" viewBox="0 0 1000 1000">
        <g transform="translate(${this.panX}, ${this.panY}) scale(${this.zoomLevel})">
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
      ${this.selectedDiscovery ? this.renderInspectionPopover(this.selectedDiscovery) : ''}
    `;
  }

  private renderInspectionPopover(d: WestMarchesDiscovery) {
    const canSeeNotes = this.canViewPrivateNotes(d);
    return html`
      <div class="inspection-popover">
        <div class="popover-header">
          <h4 class="popover-title">${d.name}</h4>
          <button class="popover-close" @click=${this.closePopover}>×</button>
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
}
