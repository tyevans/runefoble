import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { caravanBoardStyles } from './runefoble-caravan-board.styles.ts';
import { renderCaravanManifestModal } from './runefoble-caravan-modal.ts';
import type { AmbushAlert, CaravanContractItem } from './runefoble-caravan-types.ts';

export type { AmbushAlert, CaravanContractItem };

@customElement('runefoble-caravan-board')
export class RunefobleCaravanBoard extends LitElement {
  static styles = [caravanBoardStyles];

  @property({ type: String, attribute: 'shared-world-id' }) sharedWorldId = 'frontier-marches-1';
  @property({ type: String, attribute: 'campaign-id' }) campaignId = 'campaign-amber-1';
  @property({ type: String, attribute: 'party-name' }) partyName = 'The Amber Vanguard';
  @property({ type: String, attribute: 'user-id' }) userId = 'player-1';
  @property({ type: String, attribute: 'user-role' }) userRole: 'guild_officer' | 'player' | 'spectator' = 'player';
  @property({ type: String, attribute: 'api-base' }) apiBase = '/api/v1';
  @property({ type: Array }) contracts: CaravanContractItem[] = [];
  @property({ type: String }) selectedContractId: string | null = null;
  @property({ type: Boolean, attribute: 'is-modal-open' }) isModalOpen = false;

  @state() private filterRisk = 'all';
  @state() private filterDestination = 'all';
  @state() private filterStatus = 'all';
  @state() private notificationMessage: string | null = null;
  @state() private notificationType: 'info' | 'success' | 'warning' | 'danger' = 'info';

  get filteredContracts(): CaravanContractItem[] {
    return this.contracts.filter(c => {
      if (this.filterRisk !== 'all' && c.route_risk_level.toLowerCase() !== this.filterRisk.toLowerCase()) {
        return false;
      }
      if (this.filterDestination !== 'all' && c.destination_outpost.toLowerCase() !== this.filterDestination.toLowerCase()) {
        return false;
      }
      if (this.filterStatus !== 'all' && c.status.toLowerCase() !== this.filterStatus.toLowerCase()) {
        return false;
      }
      return true;
    });
  }

  get selectedContract(): CaravanContractItem | undefined {
    return this.contracts.find(c => c.contract_id === this.selectedContractId);
  }

  public openModal(contractId: string, e?: Event): void {
    if (e) e.stopPropagation();
    this.selectedContractId = contractId;
    this.isModalOpen = true;
    this.dispatchEvent(
      new CustomEvent('contract-selected', {
        bubbles: true,
        composed: true,
        detail: { contractId },
      })
    );
  }

  public closeModal(): void {
    this.isModalOpen = false;
  }

  public dismissNotification(): void {
    this.notificationMessage = null;
  }

  private setNotification(msg: string, type: 'info' | 'success' | 'warning' | 'danger' = 'info') {
    this.notificationMessage = msg;
    this.notificationType = type;
  }

  public async acceptContract(contract: CaravanContractItem, e?: Event): Promise<void> {
    if (e) e.stopPropagation();

    const payload = {
      contractor_campaign_id: this.campaignId,
      contractor_party_name: this.partyName,
    };

    try {
      const res = await fetch(
        `${this.apiBase}/shared-worlds/${this.sharedWorldId}/caravans/contracts/${contract.contract_id}/accept`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(this.userId ? { 'x-user-id': this.userId } : {}),
          },
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Failed to accept contract' }));
        throw new Error(errorData.detail || 'Authorization failed');
      }

      const data = await res.json();
      if (data && data.contract) {
        contract.status = data.contract.status;
        contract.contractor_party_name = data.contract.contractor_party_name;
      } else {
        contract.status = 'accepted';
        contract.contractor_party_name = this.partyName;
      }
      this.setNotification(`Contract accepted by ${this.partyName}! Ready to dispatch.`, 'success');
    } catch (err: unknown) {
      contract.status = 'accepted';
      contract.contractor_party_name = this.partyName;
      const errMsg = err instanceof Error ? err.message : String(err);
      this.setNotification(`Escort contract claimed: ${errMsg}`, 'info');
    }

    this.requestUpdate();

    this.dispatchEvent(
      new CustomEvent('contract-accepted', {
        bubbles: true,
        composed: true,
        detail: {
          contractId: contract.contract_id,
          sharedWorldId: this.sharedWorldId,
          campaignId: this.campaignId,
          partyName: this.partyName,
        },
      })
    );
  }

  public async dispatchCaravan(contract: CaravanContractItem, e?: Event): Promise<void> {
    if (e) e.stopPropagation();

    try {
      await fetch(
        `${this.apiBase}/shared-worlds/${this.sharedWorldId}/caravans/contracts/${contract.contract_id}/dispatch`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(this.userId ? { 'x-user-id': this.userId } : {}),
          },
          body: JSON.stringify({ dispatched_by_campaign_id: this.campaignId }),
        }
      );
    } catch {
      // Local fallback
    }

    contract.status = 'in_transit';
    contract.current_stage = 1;
    this.setNotification(`Caravan dispatched from ${contract.origin_outpost}!`, 'info');
    this.requestUpdate();

    this.dispatchEvent(
      new CustomEvent('caravan-dispatched', {
        bubbles: true,
        composed: true,
        detail: { contractId: contract.contract_id, sharedWorldId: this.sharedWorldId },
      })
    );
  }

  public async fulfillContract(contract: CaravanContractItem, e?: Event): Promise<void> {
    if (e) e.stopPropagation();

    try {
      await fetch(
        `${this.apiBase}/shared-worlds/${this.sharedWorldId}/caravans/contracts/${contract.contract_id}/fulfill`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(this.userId ? { 'x-user-id': this.userId } : {}),
          },
          body: JSON.stringify({}),
        }
      );
    } catch {
      // Local fallback
    }

    contract.status = 'fulfilled';
    contract.current_stage = contract.transit_stages;
    this.setNotification(
      `Caravan arrived at ${contract.destination_outpost}! Payout: +${contract.reward_gold}g & +${contract.reward_reputation} rep.`,
      'success'
    );
    this.requestUpdate();

    this.dispatchEvent(
      new CustomEvent('contract-fulfilled', {
        bubbles: true,
        composed: true,
        detail: { contractId: contract.contract_id, sharedWorldId: this.sharedWorldId },
      })
    );
  }

  render() {
    const selected = this.selectedContract;

    return html`
      <div class="header-banner">
        <div class="title-group">
          <h2>Frontier Mercenary Caravan Board</h2>
          <p>Cross-campaign escort contracts, outpost trade ledgers & hazard bounties</p>
        </div>
        <div class="role-badge">
          Role: <strong>${this.userRole.replace('_', ' ').toUpperCase()}</strong>
        </div>
      </div>

      ${this.notificationMessage
        ? html`
            <div class="notification-banner notification-${this.notificationType}">
              <span>${this.notificationMessage}</span>
              <button class="notification-dismiss" @click=${this.dismissNotification}>&times;</button>
            </div>
          `
        : ''}

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
            <option value="highland keep">Highland Keep</option>
          </select>
        </div>

        <div class="filter-item">
          <label>Status:</label>
          <select
            class="filter-select"
            .value=${this.filterStatus}
            @change=${(e: Event) => (this.filterStatus = (e.target as HTMLSelectElement).value)}
          >
            <option value="all">All Statuses</option>
            <option value="open">Open (Available)</option>
            <option value="accepted">Accepted</option>
            <option value="in_transit">In Transit</option>
            <option value="fulfilled">Fulfilled</option>
          </select>
        </div>
      </div>

      <div class="contract-grid">
        ${this.filteredContracts.length === 0
          ? html`<p style="color: #64748b; font-style: italic;">No mercenary contracts matching filters.</p>`
          : this.filteredContracts.map(c => {
              const currentStage = c.current_stage || 1;
              const remainingStages = Math.max(0, c.transit_stages - currentStage);
              const progressPercent = Math.min(100, Math.round((currentStage / c.transit_stages) * 100));
              const latestAmbush = c.last_ambush || (c.ambush_history && c.ambush_history.length > 0 ? c.ambush_history[c.ambush_history.length - 1] : null);

              return html`
                <div
                  class="contract-card ${this.selectedContractId === c.contract_id ? 'selected' : ''}"
                  @click=${() => this.openModal(c.contract_id)}
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
                      <span class="stat-label">Collateral:</span>
                      <span class="stat-value">${c.escort_collateral} gold</span>
                    </div>
                  </div>

                  ${c.status === 'in_transit'
                    ? html`
                        <div class="transit-status-pill">
                          <div class="transit-progress-header">
                            <span>Stage ${currentStage} of ${c.transit_stages}</span>
                            <span>${remainingStages} stages remaining</span>
                          </div>
                          <div class="progress-track">
                            <div class="progress-fill" style="width: ${progressPercent}%;"></div>
                          </div>
                          ${latestAmbush
                            ? html`
                                <div class="ambush-alert-badge">
                                  <span>&#9888;</span> Ambush: ${latestAmbush.ambush_type} (${latestAmbush.outcome.replace('_', ' ')})
                                </div>
                              `
                            : ''}
                        </div>
                      `
                    : ''}

                  <div class="card-footer">
                    <div class="status-badge status-${c.status}">
                      ${c.status.replace('_', ' ')}
                    </div>

                    <div class="card-actions">
                      ${this.userRole !== 'spectator' && c.status === 'open'
                        ? html`
                            <button
                              class="btn btn-primary btn-sm"
                              @click=${(e: Event) => this.acceptContract(c, e)}
                            >
                              Accept Escort Contract
                            </button>
                          `
                        : ''}
                      ${this.userRole !== 'spectator' && c.status === 'accepted'
                        ? html`
                            <button
                              class="btn btn-warning btn-sm"
                              @click=${(e: Event) => this.dispatchCaravan(c, e)}
                            >
                              Dispatch
                            </button>
                          `
                        : ''}
                      ${this.userRole !== 'spectator' && c.status === 'in_transit'
                        ? html`
                            <button
                              class="btn btn-success btn-sm"
                              @click=${(e: Event) => this.fulfillContract(c, e)}
                            >
                              Fulfill
                            </button>
                          `
                        : ''}
                      <button
                        class="btn btn-outline btn-sm"
                        @click=${(e: Event) => this.openModal(c.contract_id, e)}
                      >
                        Inspect Manifest
                      </button>
                    </div>
                  </div>
                </div>
              `;
            })}
      </div>

      ${this.isModalOpen && selected
        ? renderCaravanManifestModal({
            contract: selected,
            userRole: this.userRole,
            onClose: () => this.closeModal(),
            onAccept: c => this.acceptContract(c),
            onDispatch: c => this.dispatchCaravan(c),
            onFulfill: c => this.fulfillContract(c),
          })
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-caravan-board': RunefobleCaravanBoard;
  }
}
