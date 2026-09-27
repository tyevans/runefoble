import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { type WestMarchesDiscovery, PARTY_COLORS } from './types.ts';

@customElement('runefoble-expedition-chronicle')
export class RunefobleExpeditionChronicle extends LitElement {
  createRenderRoot() { return this; }

  @property({ type: Array }) discoveries: WestMarchesDiscovery[] = [];

  private getPartyColor(name: string): string {
    return PARTY_COLORS[name] || '#2a9d8f';
  }

  render() {
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
