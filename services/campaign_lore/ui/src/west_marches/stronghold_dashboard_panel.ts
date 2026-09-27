import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { strongholdStyles } from './styles/stronghold.styles.ts';
import type { WestMarchesOutpost } from './types.ts';

@customElement('runefoble-stronghold-dashboard-panel')
export class RunefobleStrongholdDashboardPanel extends LitElement {
  static styles = strongholdStyles;

  @property({ type: Object }) outpost: WestMarchesOutpost | null = null;
  @property({ type: Array }) outposts: WestMarchesOutpost[] = [];
  @property({ type: String }) frontierRegion = 'The Untamed Wilds';
  @property({ type: String }) sharedWorldId = '';

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

  render() {
    const outpost = this.outpost || this.outposts[0] || {
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

    const resources = outpost.stored_resources || { gold: 100, timber: 20 };

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

        <div class="treasury-bar">
          <span style="font-weight: 800;">Communal Treasury:</span>
          ${Object.entries(resources).map(([resKey, amount]) => html`
            <div class="treasury-item">
              <span>${resKey === 'gold' ? '🪙' : resKey === 'timber' ? '🪵' : resKey === 'stone' ? '🪨' : '🧪'}</span>
              <span>${resKey.replace('_', ' ').toUpperCase()}: <strong>${amount}</strong></span>
            </div>
          `)}
        </div>

        <div class="facility-grid">
          ${Object.entries(outpost.facilities).map(([facId, tier]) => {
            const facTitle = facId.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
            const matchedBoons = (outpost.boons || []).filter((b) => b.toLowerCase().includes(facId.split('_')[0]));
            return html`
              <div class="facility-card">
                <div class="facility-header">
                  <span class="facility-title">${facTitle}</span>
                  <span class="facility-tier-badge">Tier ${tier}</span>
                </div>
                <div><strong>Shared Boons:</strong></div>
                <ul class="boons-list">
                  ${matchedBoons.length > 0
                    ? matchedBoons.map((boon) => html`<li>${boon}</li>`)
                    : html`<li>Active baseline facility bonus (Lv ${tier})</li>`}
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
}
