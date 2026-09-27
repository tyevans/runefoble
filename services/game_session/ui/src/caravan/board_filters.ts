import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { layoutStyles } from './styles/layout.styles.ts';

@customElement('runefoble-caravan-board-filters')
export class RunefobleCaravanBoardFilters extends LitElement {
  static styles = [layoutStyles];

  @property({ type: String }) searchQuery = '';
  @property({ type: String }) filterRisk = 'all';
  @property({ type: String }) filterDestination = 'all';
  @property({ type: String }) filterStatus = 'all';
  @property({ type: String }) filterCargo = 'all';

  private emitChange() {
    this.dispatchEvent(
      new CustomEvent('filters-changed', {
        bubbles: true,
        composed: true,
        detail: {
          searchQuery: this.searchQuery,
          filterRisk: this.filterRisk,
          filterDestination: this.filterDestination,
          filterStatus: this.filterStatus,
          filterCargo: this.filterCargo,
        },
      })
    );
  }

  render() {
    return html`
      <div class="filters-toolbar">
        <div class="filter-item">
          <label>Search:</label>
          <input
            type="text"
            class="search-input"
            placeholder="Route or Cargo..."
            .value=${this.searchQuery}
            @input=${(e: Event) => {
              this.searchQuery = (e.target as HTMLInputElement).value;
              this.emitChange();
            }}
          />
        </div>

        <div class="filter-item">
          <label>Risk Level:</label>
          <select
            class="filter-select"
            .value=${this.filterRisk}
            @change=${(e: Event) => {
              this.filterRisk = (e.target as HTMLSelectElement).value;
              this.emitChange();
            }}
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
            @change=${(e: Event) => {
              this.filterDestination = (e.target as HTMLSelectElement).value;
              this.emitChange();
            }}
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
            @change=${(e: Event) => {
              this.filterStatus = (e.target as HTMLSelectElement).value;
              this.emitChange();
            }}
          >
            <option value="all">All Statuses</option>
            <option value="open">Open (Available)</option>
            <option value="accepted">Accepted</option>
            <option value="in_transit">In Transit</option>
            <option value="fulfilled">Fulfilled</option>
          </select>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-caravan-board-filters': RunefobleCaravanBoardFilters;
  }
}
