import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { caravanBoardStyles } from './runefoble-caravan-board.styles.ts';
import { apiAcceptContract, apiDispatchCaravan, apiFulfillContract } from './caravan/caravan_api.ts';
import './caravan/contract_card.ts';
import './caravan/dispatch_modal.ts';
import './caravan/board_filters.ts';
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

  @state() public searchQuery = ''; @state() public filterRisk = 'all';
  @state() public filterDestination = 'all'; @state() public filterStatus = 'all';
  @state() private notificationMessage: string | null = null; @state() private notificationType: 'info' | 'success' | 'warning' | 'danger' = 'info';

  private get apiCtx() {
    return { apiBase: this.apiBase, sharedWorldId: this.sharedWorldId, campaignId: this.campaignId, partyName: this.partyName, userId: this.userId };
  }

  get filteredContracts(): CaravanContractItem[] {
    return this.contracts.filter(c => {
      if (this.filterRisk !== 'all' && c.route_risk_level.toLowerCase() !== this.filterRisk.toLowerCase()) return false;
      if (this.filterDestination !== 'all' && c.destination_outpost.toLowerCase() !== this.filterDestination.toLowerCase()) return false;
      if (this.filterStatus !== 'all' && c.status.toLowerCase() !== this.filterStatus.toLowerCase()) return false;
      return !this.searchQuery || `${c.origin_outpost} ${c.destination_outpost} ${Object.keys(c.cargo || {}).join(' ')}`.toLowerCase().includes(this.searchQuery.toLowerCase());
    });
  }

  get selectedContract(): CaravanContractItem | undefined {
    return this.contracts.find(c => c.contract_id === this.selectedContractId);
  }

  public openModal(contractId: string, e?: Event): void {
    if (e) e.stopPropagation();
    this.selectedContractId = contractId;
    this.isModalOpen = true;
    this.dispatchEvent(new CustomEvent('contract-selected', { bubbles: true, composed: true, detail: { contractId } }));
  }
  public closeModal(): void { this.isModalOpen = false; }
  public dismissNotification(): void { this.notificationMessage = null; }

  public async acceptContract(contract: CaravanContractItem, e?: Event): Promise<void> {
    if (e) e.stopPropagation();
    try {
      await apiAcceptContract(this.apiCtx, contract);
      this.notificationMessage = `Contract accepted by ${this.partyName}! Ready to dispatch.`;
      this.notificationType = 'success';
    } catch (err: unknown) {
      contract.status = 'accepted';
      contract.contractor_party_name = this.partyName;
      this.notificationMessage = `Escort contract claimed: ${err instanceof Error ? err.message : String(err)}`;
      this.notificationType = 'info';
    }
    this.requestUpdate();
    this.dispatchEvent(new CustomEvent('contract-accepted', { bubbles: true, composed: true, detail: { contractId: contract.contract_id, sharedWorldId: this.sharedWorldId, campaignId: this.campaignId, partyName: this.partyName } }));
  }

  public async dispatchCaravan(contract: CaravanContractItem, e?: Event): Promise<void> {
    if (e) e.stopPropagation();
    await apiDispatchCaravan(this.apiCtx, contract);
    this.notificationMessage = `Caravan dispatched from ${contract.origin_outpost}!`;
    this.notificationType = 'info';
    this.requestUpdate();
    this.dispatchEvent(new CustomEvent('caravan-dispatched', { bubbles: true, composed: true, detail: { contractId: contract.contract_id, sharedWorldId: this.sharedWorldId } }));
  }

  public async fulfillContract(contract: CaravanContractItem, e?: Event): Promise<void> {
    if (e) e.stopPropagation();
    await apiFulfillContract(this.apiCtx, contract);
    this.notificationMessage = `Caravan arrived at ${contract.destination_outpost}! Payout: +${contract.reward_gold}g & +${contract.reward_reputation} rep.`;
    this.notificationType = 'success';
    this.requestUpdate();
    this.dispatchEvent(new CustomEvent('contract-fulfilled', { bubbles: true, composed: true, detail: { contractId: contract.contract_id, sharedWorldId: this.sharedWorldId } }));
  }

  render() {
    return html`
      <div class="header-banner">
        <div class="title-group">
          <h2>Frontier Mercenary Caravan Board</h2>
          <p>Cross-campaign escort contracts, outpost trade ledgers & hazard bounties</p>
        </div>
        <div class="role-badge">Role: <strong>${this.userRole.replace('_', ' ').toUpperCase()}</strong></div>
      </div>
      ${this.notificationMessage ? html`
        <div class="notification-banner notification-${this.notificationType}">
          <span>${this.notificationMessage}</span>
          <button class="notification-dismiss" @click=${this.dismissNotification}>&times;</button>
        </div>` : ''}
      <runefoble-caravan-board-filters
        .searchQuery=${this.searchQuery} .filterRisk=${this.filterRisk}
        .filterDestination=${this.filterDestination} .filterStatus=${this.filterStatus}
        @filters-changed=${(e: CustomEvent) => { Object.assign(this, e.detail); }}
      ></runefoble-caravan-board-filters>
      <div class="contract-grid">
        ${this.filteredContracts.length === 0
          ? html`<p class="empty-notice">No mercenary contracts matching filters.</p>`
          : this.filteredContracts.map(c => html`
            <runefoble-caravan-contract-card
              .contract=${c} .selected=${this.selectedContractId === c.contract_id} .userRole=${this.userRole}
              @contract-selected=${(e: CustomEvent) => this.openModal(e.detail.contractId)}
              @contract-inspect=${(e: CustomEvent) => this.openModal(e.detail.contractId)}
              @contract-accept=${(e: CustomEvent) => this.acceptContract(e.detail.contract)}
              @contract-dispatch=${(e: CustomEvent) => this.dispatchCaravan(e.detail.contract)}
              @contract-fulfill=${(e: CustomEvent) => this.fulfillContract(e.detail.contract)}
            ></runefoble-caravan-contract-card>`)}
      </div>
      <runefoble-caravan-dispatch-modal
        .contract=${this.selectedContract || null}
        .isOpen=${this.isModalOpen && Boolean(this.selectedContract)}
        .userRole=${this.userRole} .partyName=${this.partyName}
        @close-modal=${() => this.closeModal()}
        @contract-accept=${(e: CustomEvent) => this.acceptContract(e.detail.contract)}
        @contract-dispatch=${(e: CustomEvent) => this.dispatchCaravan(e.detail.contract)}
        @contract-fulfill=${(e: CustomEvent) => this.fulfillContract(e.detail.contract)}
      ></runefoble-caravan-dispatch-modal>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-caravan-board': RunefobleCaravanBoard;
  }
}
