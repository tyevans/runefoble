import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { factionRadarStyles } from './runefoble-faction-radar.styles.ts';
import type { FactionData, WorldTickData } from './faction_radar/types.ts';
import { renderRadarChart } from './faction_radar/radar-svg.template.ts';
import { renderFactionCards } from './faction_radar/faction-details.template.ts';
import { renderDmDrawer, renderRumors } from './faction_radar/bulletin-drawer.template.ts';

export * from './faction_radar/types.ts';

@customElement('runefoble-faction-radar')
export class RunefobleFactionRadar extends LitElement {
  @property({ type: String }) campaignId = '';
  @property({ type: Array }) factions: FactionData[] = [];
  @property({ type: Object }) bulletin: WorldTickData | null = null;
  @property({ type: Boolean }) isDm = false;
  @property({ type: String }) selectedFactionId = '';
  @property({ type: Boolean }) isDrawerOpen = false;
  @property({ type: Array }) tavernRumors: string[] = [];

  static styles = factionRadarStyles;

  private selectFaction(faction: FactionData) {
    this.selectedFactionId = faction.faction_id;
    this.dispatchEvent(
      new CustomEvent('faction-selected', {
        detail: { factionId: faction.faction_id, faction },
        bubbles: true,
        composed: true,
      })
    );
  }

  private toggleDrawer() {
    this.isDrawerOpen = !this.isDrawerOpen;
    this.dispatchEvent(
      new CustomEvent('drawer-toggled', {
        detail: { isOpen: this.isDrawerOpen },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleTriggerWorldTick() {
    this.dispatchEvent(
      new CustomEvent('world-tick-requested', {
        detail: { campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private getActiveFactions(): FactionData[] {
    return this.factions.length > 0 ? this.factions : (this.bulletin?.factions || []);
  }

  private getRumorsList(): string[] {
    if (this.tavernRumors?.length) return this.tavernRumors;
    if (this.bulletin?.tavern_rumors?.length) return this.bulletin.tavern_rumors;
    return [];
  }

  render() {
    const activeFactions = this.getActiveFactions();
    const tickNum = this.bulletin?.tick_number ?? 0;

    return html`
      <div class="header">
        <div class="title-group">
          <h3>Autonomous NPC Faction Radar</h3>
          <span class="badge badge-tick">${tickNum > 0 ? `Tick #${tickNum}` : 'Standby'}</span>
          <span class="badge ${this.isDm ? 'badge-dm' : 'badge-player'}">
            ${this.isDm ? 'DM Clearance' : 'Player View'}
          </span>
        </div>
        <div class="controls-group">
          ${this.isDm
            ? html`<button class="btn btn-primary" @click="${this.handleTriggerWorldTick}">Advance World Tick</button>`
            : ''}
          <button class="btn ${this.isDrawerOpen ? 'btn-drawer active' : 'btn-secondary'}" @click="${this.toggleDrawer}">
            ${this.isDrawerOpen ? 'Hide Intel' : 'DM Intel Bulletin'}
          </button>
        </div>
      </div>
      <div class="radar-grid">
        ${renderRadarChart({
          factions: activeFactions,
          selectedFactionId: this.selectedFactionId,
          onSelectFaction: (f) => this.selectFaction(f),
        })}
        ${renderFactionCards({
          factions: activeFactions,
          selectedFactionId: this.selectedFactionId,
          onSelectFaction: (f) => this.selectFaction(f),
        })}
      </div>
      ${renderDmDrawer({
        isOpen: this.isDrawerOpen,
        isDm: this.isDm,
        bulletin: this.bulletin,
        onClose: () => this.toggleDrawer(),
      })}
      ${renderRumors(this.getRumorsList())}
    `;
  }
}
