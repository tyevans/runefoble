import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { cardStyles } from './styles/card.styles.ts';
import type { CaravanContractItem } from '../runefoble-caravan-types.ts';

@customElement('runefoble-caravan-contract-card')
export class RunefobleCaravanContractCard extends LitElement {
  static styles = [cardStyles];

  @property({ type: Object }) contract!: CaravanContractItem;
  @property({ type: Boolean }) selected = false;
  @property({ type: String }) userRole: 'guild_officer' | 'player' | 'spectator' = 'player';

  private handleCardClick() {
    this.dispatchEvent(new CustomEvent('contract-selected', {
      bubbles: true, composed: true, detail: { contractId: this.contract.contract_id },
    }));
  }

  private handleAction(e: Event, action: 'accept' | 'dispatch' | 'fulfill' | 'inspect') {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent(`contract-${action}`, {
      bubbles: true, composed: true, detail: { contract: this.contract, contractId: this.contract.contract_id },
    }));
  }

  render() {
    if (!this.contract) return html``;
    const c = this.contract;
    const currentStage = c.current_stage || 1;
    const remainingStages = Math.max(0, c.transit_stages - currentStage);
    const progressPercent = Math.min(100, Math.round((currentStage / c.transit_stages) * 100));
    const latestAmbush = c.last_ambush || (c.ambush_history && c.ambush_history.length > 0 ? c.ambush_history[c.ambush_history.length - 1] : null);

    return html`
      <div class="contract-card ${this.selected ? 'selected' : ''}" @click=${this.handleCardClick}>
        <div class="card-top">
          <h3 class="route-title">${c.origin_outpost} &rarr; ${c.destination_outpost}</h3>
          <span class="risk-badge risk-${c.route_risk_level.toLowerCase()}">${c.route_risk_level}</span>
        </div>

        <div class="card-stats">
          <div class="stat-row"><span class="stat-label">Cargo Value:</span><span class="stat-value">${c.cargo_value}g</span></div>
          <div class="stat-row"><span class="stat-label">Bounty Escrow:</span><span class="stat-value gold-tag">+${c.reward_gold} gold</span></div>
          <div class="stat-row"><span class="stat-label">Reputation:</span><span class="stat-value rep-tag">+${c.reward_reputation} rep</span></div>
          <div class="stat-row"><span class="stat-label">Collateral:</span><span class="stat-value">${c.escort_collateral} gold</span></div>
        </div>

        ${c.status === 'in_transit' ? html`
          <div class="transit-status-pill">
            <div class="transit-progress-header">
              <span>Stage ${currentStage} of ${c.transit_stages}</span>
              <span>${remainingStages} stages remaining</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width: ${progressPercent}%;"></div></div>
            ${latestAmbush ? html`
              <div class="ambush-alert-badge">
                <span>&#9888;</span> Ambush: ${latestAmbush.ambush_type} (${latestAmbush.outcome.replace('_', ' ')})
              </div>` : ''}
          </div>` : ''}

        <div class="card-footer">
          <div class="status-badge status-${c.status}">${c.status.replace('_', ' ')}</div>
          <div class="card-actions">
            ${this.userRole !== 'spectator' && c.status === 'open' ? html`
              <button class="btn btn-primary btn-sm" @click=${(e: Event) => this.handleAction(e, 'accept')}>Accept Escort Contract</button>` : ''}
            ${this.userRole !== 'spectator' && c.status === 'accepted' ? html`
              <button class="btn btn-warning btn-sm" @click=${(e: Event) => this.handleAction(e, 'dispatch')}>Dispatch</button>` : ''}
            ${this.userRole !== 'spectator' && c.status === 'in_transit' ? html`
              <button class="btn btn-success btn-sm" @click=${(e: Event) => this.handleAction(e, 'fulfill')}>Fulfill</button>` : ''}
            <button class="btn btn-outline btn-sm" @click=${(e: Event) => this.handleAction(e, 'inspect')}>Inspect Manifest</button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-caravan-contract-card': RunefobleCaravanContractCard;
  }
}
