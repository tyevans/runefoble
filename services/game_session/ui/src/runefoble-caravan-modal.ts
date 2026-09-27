import { html, type TemplateResult } from 'lit';
import type { CaravanContractItem } from './runefoble-caravan-types.ts';

export interface CaravanModalOptions {
  contract: CaravanContractItem;
  userRole: string;
  onClose: () => void;
  onAccept: (c: CaravanContractItem) => void;
  onDispatch: (c: CaravanContractItem) => void;
  onFulfill: (c: CaravanContractItem) => void;
}

export function renderCaravanManifestModal(opts: CaravanModalOptions): TemplateResult {
  const { contract, userRole, onClose, onAccept, onDispatch, onFulfill } = opts;
  const currentStage = contract.current_stage || 1;
  const remainingStages = Math.max(0, contract.transit_stages - currentStage);
  const progressPercent = Math.min(100, Math.round((currentStage / contract.transit_stages) * 100));

  return html`
    <div class="modal-backdrop" @click=${onClose}>
      <div class="manifest-modal" @click=${(e: Event) => e.stopPropagation()}>
        <div class="modal-header">
          <div>
            <h3>Caravan Manifest: ${contract.origin_outpost} &rarr; ${contract.destination_outpost}</h3>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
              Contract ID: ${contract.contract_id}
            </div>
          </div>
          <button class="close-btn" @click=${onClose}>&times;</button>
        </div>

        <div class="modal-section">
          <div class="modal-section-title">Route Information</div>
          <div class="route-summary-box">
            <div>Departure Settlement: <strong>${contract.origin_outpost}</strong></div>
            <div>Destination Stronghold: <strong>${contract.destination_outpost}</strong></div>
            <div>
              Hazard Rating:
              <span class="risk-badge risk-${contract.route_risk_level.toLowerCase()}">
                ${contract.route_risk_level.toUpperCase()}
              </span>
            </div>
            <div>Transit Stages: <strong>${contract.transit_stages} stages</strong></div>
          </div>
        </div>

        <div class="modal-section">
          <div class="modal-section-title">Cargo Inventory (Total Value: ${contract.cargo_value} Gold)</div>
          <div class="cargo-list">
            ${Object.entries(contract.cargo).map(
              ([item, qty]) => html`
                <div class="cargo-pill">
                  ${item.replace('_', ' ').toUpperCase()}: <strong>x${qty}</strong>
                </div>
              `
            )}
          </div>
        </div>

        <div class="modal-section">
          <div class="modal-section-title">Escort Fee & Escrow</div>
          <div class="route-summary-box">
            <div>Escort Fee Payout: <strong class="gold-tag">+${contract.reward_gold} Gold</strong></div>
            <div>Reputation Bonus: <strong class="rep-tag">+${contract.reward_reputation} Rep</strong></div>
            <div>Required Collateral: <strong>${contract.escort_collateral} Gold</strong></div>
            <div>Current Status: <strong>${contract.status.toUpperCase()}</strong></div>
          </div>
        </div>

        ${contract.contractor_party_name
          ? html`
              <div class="modal-section">
                <div class="modal-section-title">Escort Contractor</div>
                <div style="font-size: 0.85rem; font-weight: 700;">
                  Assigned Party: ${contract.contractor_party_name}
                </div>
              </div>
            `
          : ''}

        ${contract.status === 'in_transit'
          ? html`
              <div class="modal-section">
                <div class="modal-section-title">Transit Status</div>
                <div class="transit-status-pill">
                  <div class="transit-progress-header">
                    <span>Stage ${currentStage} of ${contract.transit_stages}</span>
                    <span>${remainingStages} stages remaining</span>
                  </div>
                  <div class="progress-track">
                    <div class="progress-fill" style="width: ${progressPercent}%;"></div>
                  </div>
                </div>
              </div>
            `
          : ''}

        ${contract.ambush_history && contract.ambush_history.length > 0
          ? html`
              <div class="modal-section">
                <div class="modal-section-title">Ambush Encounter Alerts</div>
                <div class="ambush-log">
                  ${contract.ambush_history.map(
                    a => html`
                      <div class="ambush-log-entry">
                        <strong>Stage ${a.stage_index}:</strong> ${a.ambush_type} (Danger: ${a.danger_level}) &mdash;
                        <em>${a.outcome.replace('_', ' ').toUpperCase()}</em>
                        ${a.notes ? html`<p style="margin: 2px 0 0 0;">${a.notes}</p>` : ''}
                      </div>
                    `
                  )}
                </div>
              </div>
            `
          : ''}

        <div class="modal-footer">
          ${userRole !== 'spectator' && contract.status === 'open'
            ? html`
                <button class="btn btn-primary" @click=${() => onAccept(contract)}>
                  Accept Escort Contract
                </button>
              `
            : ''}
          ${userRole !== 'spectator' && contract.status === 'accepted'
            ? html`
                <button class="btn btn-warning" @click=${() => onDispatch(contract)}>
                  Dispatch Caravan
                </button>
              `
            : ''}
          ${userRole !== 'spectator' && contract.status === 'in_transit'
            ? html`
                <button class="btn btn-success" @click=${() => onFulfill(contract)}>
                  Fulfill & Deliver Cargo
                </button>
              `
            : ''}
          <button class="btn btn-outline" @click=${onClose}>Close</button>
        </div>
      </div>
    </div>
  `;
}
