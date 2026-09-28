import { html } from 'lit';
import type { StrongholdStatusProps } from './types.ts';

export function renderStrongholdStatus(props: StrongholdStatusProps) {
  const facilities = [
    { id: 'watchtower', name: 'Watchtower' },
    { id: 'herbal_rack', name: 'Herbal Drying Rack' },
    { id: 'arcane_forge', name: 'Arcane Forge' },
  ];

  return html`
    <div class="panel">
      <div class="panel-header"><span>🏰</span> Campsite Fortifications</div>
      <div class="facility-list">
        ${facilities.map(
          (fac) => html`
            <div class="facility-row">
              <div>
                <span class="facility-name">${fac.name}</span>
                <span class="facility-tier">Tier ${props.strongholdFacilities[fac.id] || 0}</span>
              </div>
              <button class="btn" @click="${() => props.onUpgrade(fac.id)}">
                Upgrade
              </button>
            </div>
          `
        )}
      </div>
    </div>
  `;
}
