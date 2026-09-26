import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface LoreEntry {
  id: string;
  title: string;
  text: string;
  entities: string[];
  graphContext?: string[];
  isSecret?: boolean;
}

@customElement('runefoble-campaign-codex')
export class RunefobleCampaignCodex extends LitElement {
  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      padding: 16px;
      color: var(--rf-text-primary, #121212);
      width: 480px;
      max-width: 100%;
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      box-sizing: border-box;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      margin-bottom: 12px;
    }
    .title {
      font-size: 1.1rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    .badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 2px 8px;
      border: 1px solid var(--rf-border-color, #121212);
      background: var(--rf-accent-tertiary, #ffb703);
    }
    .search-box {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }
    .search-input {
      flex: 1;
      padding: 8px 12px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      font-family: inherit;
      font-size: 0.85rem;
    }
    .search-btn {
      padding: 8px 16px;
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
      font-weight: 700;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      cursor: pointer;
      box-shadow: 2px 2px 0px #121212;
    }
    .entry-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 400px;
      overflow-y: auto;
    }
    .entry-card {
      border: 1px solid var(--rf-border-color, #121212);
      padding: 10px;
      background: #fafafa;
    }
    .entry-title {
      font-weight: 700;
      font-size: 0.95rem;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .secret-tag {
      font-size: 0.7rem;
      color: #fff;
      background: #d90429;
      padding: 1px 6px;
      font-weight: 700;
    }
    .entry-text {
      font-size: 0.85rem;
      line-height: 1.4;
      margin-bottom: 6px;
    }
    .entity-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .entity-chip {
      font-size: 0.7rem;
      background: #e2eafc;
      border: 1px solid #121212;
      padding: 1px 6px;
      font-weight: 600;
    }
    .graph-rel {
      font-size: 0.75rem;
      color: #555;
      font-family: monospace;
      margin-top: 4px;
    }
  `;

  @property({ type: String })
  campaignId = '';

  @property({ type: Boolean })
  isDM = false;

  @property({ type: Array })
  entries: LoreEntry[] = [];

  @state()
  private searchQuery = '';

  private handleSearchInput(e: Event) {
    this.searchQuery = (e.target as HTMLInputElement).value;
  }

  private handleSearch() {
    this.dispatchEvent(
      new CustomEvent('lore-search', {
        detail: { query: this.searchQuery, campaignId: this.campaignId },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const filtered = this.entries.filter((entry) => {
      if (entry.isSecret && !this.isDM) return false;
      if (!this.searchQuery) return true;
      return (
        entry.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        entry.text.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        entry.entities.some((e) => e.toLowerCase().includes(this.searchQuery.toLowerCase()))
      );
    });

    return html`
      <div class="header">
        <span class="title">Campaign Lore Codex</span>
        <span class="badge">${this.isDM ? 'DM Secret Access' : 'Player Codex'}</span>
      </div>

      <div class="search-box">
        <input
          type="text"
          class="search-input"
          placeholder="Search world history, NPCs, factions..."
          .value=${this.searchQuery}
          @input=${this.handleSearchInput}
          @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.handleSearch()}
        />
        <button class="search-btn" @click=${this.handleSearch}>Search</button>
      </div>

      <div class="entry-list">
        ${filtered.length === 0
          ? html`<div style="font-size: 0.85rem; color: #666; text-align: center; padding: 16px;">
              No lore records found.
            </div>`
          : filtered.map(
              (entry) => html`
                <div class="entry-card">
                  <div class="entry-title">
                    <span>${entry.title}</span>
                    ${entry.isSecret ? html`<span class="secret-tag">DM SECRET</span>` : ''}
                  </div>
                  <div class="entry-text">${entry.text}</div>
                  <div class="entity-chips">
                    ${entry.entities.map(
                      (ent) => html`<span class="entity-chip">${ent}</span>`
                    )}
                  </div>
                  ${entry.graphContext && entry.graphContext.length > 0
                    ? html`
                        <div class="graph-rel">
                          ${entry.graphContext.map((rel) => html`<div>🔗 ${rel}</div>`)}
                        </div>
                      `
                    : ''}
                </div>
              `
            )}
      </div>
    `;
  }
}
