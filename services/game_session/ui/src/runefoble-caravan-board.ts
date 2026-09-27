import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { caravanBoardStyles } from './runefoble-caravan-board.styles.ts';

export interface CaravanContractItem {
  contract_id: string;
  origin_outpost: string;
  destination_outpost: string;
  cargo: Record<string, number>;
  cargo_value: number;
  route_risk_level: 'low' | 'medium' | 'high' | 'deadly';
  transit_stages: number;
  current_stage?: number;
  escort_collateral: number;
  reward_gold: number;
  reward_reputation: number;
  posted_by_campaign_id?: string;
  contractor_party_name?: string;
  status: 'open' | 'accepted' | 'in_transit' | 'fulfilled' | 'failed';
  expires_in_turns?: number;
}

@customElement('runefoble-caravan-board')
export class RunefobleCaravanBoard extends LitElement {
  static styles = [caravanBoardStyles];

  @property({ type: String, attribute: 'shared-world-id' }) sharedWorldId = 'frontier-marches-1';
  @property({ type: String, attribute: 'user-role' }) userRole: 'guild_officer' | 'player' | 'spectator' = 'player';
  @property({ type: Array }) contracts: CaravanContractItem[] = [];
  @property({ type: String }) selectedContractId: string | null = null;

  @state() private filterRisk = 'all';
  @state() private filterDestination = 'all';

  get filteredContracts(): CaravanContractItem[] {
    return this.contracts.filter(c => {
      if (this.filterRisk !== 'all' && c.route_risk_level.toLowerCase() !== this.filterRisk.toLowerCase()) {
        return false;
      }
      if (this.filterDestination !== 'all' && c.destination_outpost.toLowerCase() !== this.filterDestination.toLowerCase()) {
        return false;
      }
      return true;
    });
  }

  get selectedContract(): CaravanContractItem | undefined {
    return this.contracts.find(c => c.contract_id === this.selectedContractId);
  }

  private selectContract(contractId: string) {
    this.selectedContractId = contractId;
    this.dispatchEvent(
      new CustomEvent('contract-selected', {
        bubbles: true,
        composed: true,
        detail: { contractId },
      })
    );
  }

  private claimContract(contract: CaravanContractItem) {
    this.dispatchEvent(
      new CustomEvent('contract-claimed', {
        bubbles: true,
        composed: true,
        detail: {
          contractId: contract.contract_id,
          sharedWorldId: this.sharedWorldId,
        },
      })
    );
  }

  private dispatchCaravan(contract: CaravanContractItem) {
    this.dispatchEvent(
      new CustomEvent('caravan-dispatched', {
        bubbles: true,
        composed: true,
        detail: {
          contractId: contract.contract_id,
          sharedWorldId: this.sharedWorldId,
        },
      })
    );
  }

  private fulfillContract(contract: CaravanContractItem) {
    this.dispatchEvent(
      new CustomEvent('contract-fulfilled', {
        bubbles: true,
        composed: true,
        detail: {
          contractId: contract.contract_id,
          sharedWorldId: this.sharedWorldId,
        },
      })
    );
  }

  render() {
    const selected = this.selectedContract;

    return html`
      <div class="header-banner">
        <div class="title-group">
          <h2>Frontier Mercenary Caravan Board</h2>
          <p>Asynchronous bounties, regional supply escorts, and outpost trade ledgers</p>
        </div>
        <div class="role-badge">
          Role: <strong>${this.userRole.replace('_', ' ').toUpperCase()}</strong>
        </div>
      </div>

      <div class="filters-toolbar">
        <div class="filter-item">
          <label>Risk Level:</label>
          <select
            class="filter-select"
            .value=${this.filterRisk}
            @change=${(e: Event) => (this.filterRisk = (e.target as HTMLSelectElement).value)}
          >
            <option value="all">All Hazards</option>
            <option value="low">Low (Safe Trails)</option>
            <option value="medium">Medium (Wilderness)</option>
            <option value="high">High (Bandit Country)</option>
            <option value="deadly">Deadly (Monster Lairs)</option>
          </select>
        </div>

        <div class="filter-item">
          <label>Destination:</label>
          <select
            class="filter-select"
            .value=${this.filterDestination}
            @change=${(e: Event) => (this.filterDestination = (e.target as HTMLSelectElement).value)}
          >
            <option value="all">All Outposts</option>
            <option value="ironford">Ironford Outpost</option>
            <option value="shadowfen">Shadowfen Sanctuary</option>
            <option value="highland_keep">Highland Keep</option>
          </select>
        </div>
      </div>

      <div class="contract-grid">
        ${this.filteredContracts.length === 0
          ? html`<p style="color: #64748b; font-style: italic;">No mercenary contracts matching filters.</p>`
          : this.filteredContracts.map(
              c => html`
                <div
                  class="contract-card ${this.selectedContractId === c.contract_id ? 'selected' : ''}"
                  @click=${() => this.selectContract(c.contract_id)}
                >
                  <div class="card-top">
                    <h3 class="route-title">${c.origin_outpost} &rarr; ${c.destination_outpost}</h3>
                    <span class="risk-badge risk-${c.route_risk_level.toLowerCase()}">
                      ${c.route_risk_level}
                    </span>
                  </div>

                  <div class="card-stats">
                    <div class="stat-row">
                      <span class="stat-label">Cargo Value:</span>
                      <span class="stat-value">${c.cargo_value}g</span>
                    </div>
                    <div class="stat-row">
                      <span class="stat-label">Bounty Escrow:</span>
                      <span class="stat-value gold-tag">+${c.reward_gold} gold</span>
                    </div>
                    <div class="stat-row">
                      <span class="stat-label">Reputation:</span>
                      <span class="stat-value rep-tag">+${c.reward_reputation} rep</span>
                    </div>
                    <div class="stat-row">
                      <span class="stat-label">Stages:</span>
                      <span class="stat-value">${c.transit_stages} transit stages</span>
                    </div>
                  </div>

                  <div class="status-badge status-${c.status}">
                    ${c.status.replace('_', ' ')}
                  </div>
                </div>
              `
            )}
      </div>

      ${selected
        ? html`
            <div class="manifest-drawer">
              <div class="drawer-header">
                <h3 style="margin: 0; font-size: 1.1rem; text-transform: uppercase;">
                  Contract Manifest: ${selected.origin_outpost} to ${selected.destination_outpost}
                </h3>
                <span class="risk-badge risk-${selected.route_risk_level.toLowerCase()}">
                  ${selected.route_risk_level.toUpperCase()} RISK
                </span>
              </div>

              <p style="font-size: 0.85rem; margin-bottom: 8px;"><strong>Cargo Manifest:</strong></p>
              <div class="cargo-list">
                ${Object.entries(selected.cargo).map(
                  ([item, qty]) => html`
                    <div class="cargo-pill">
                      ${item.replace('_', ' ').toUpperCase()}: <strong>x${qty}</strong>
                    </div>
                  `
                )}
              </div>

              <div class="stat-row" style="font-size: 0.85rem;">
                <span>Required Collateral: <strong>${selected.escort_collateral} gold</strong></span>
                <span>Contract Status: <strong>${selected.status.toUpperCase()}</strong></span>
              </div>

              ${this.userRole !== 'spectator'
                ? html`
                    <div class="action-buttons">
                      ${selected.status === 'open'
                        ? html`
                            <button
                              class="btn btn-primary"
                              @click=${() => this.claimContract(selected)}
                            >
                              Claim Escort Contract
                            </button>
                          `
                        : ''}
                      ${selected.status === 'accepted'
                        ? html`
                            <button
                              class="btn btn-warning"
                              @click=${() => this.dispatchCaravan(selected)}
                            >
                              Dispatch Caravan
                            </button>
                          `
                        : ''}
                      ${selected.status === 'in_transit'
                        ? html`
                            <button
                              class="btn btn-success"
                              @click=${() => this.fulfillContract(selected)}
                            >
                              Fulfill & Deliver Cargo
                            </button>
                          `
                        : ''}
                    </div>
                  `
                : ''}
            </div>
          `
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-caravan-board': RunefobleCaravanBoard;
  }
}
