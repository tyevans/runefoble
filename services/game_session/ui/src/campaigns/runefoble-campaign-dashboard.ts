import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignDashboardStyles } from './runefoble-campaign-dashboard.styles.ts';
import type { CampaignItem, RoleFilter, SelectCampaignEventDetail, CreateCampaignPayload } from './types.ts';
import './runefoble-campaign-creator.ts';

@customElement('runefoble-campaign-dashboard')
export class RunefobleCampaignDashboard extends LitElement {
  static styles = campaignDashboardStyles;

  @property({ type: Array }) campaigns: CampaignItem[] = [];
  @property({ type: String }) activeFilter: RoleFilter = 'all';
  @property({ type: String }) searchQuery = '';
  @property({ type: Boolean }) loading = false;
  @property({ type: String, attribute: 'user-id' }) userId = '';
  @property({ type: Boolean, attribute: 'show-creator' }) showCreator = false;

  @state() private isCreatorOpen = false;

  get isDMing(): (c: CampaignItem) => boolean {
    return (c: CampaignItem) => {
      const r = (c.role || '').toLowerCase();
      if (r === 'owner' || r === 'dungeon_master' || r === 'dm') return true;
      if (this.userId && c.owner_id === this.userId) return true;
      return false;
    };
  }

  get filteredCampaigns(): CampaignItem[] {
    return this.campaigns.filter((c) => {
      // Role filter
      if (this.activeFilter === 'dming') {
        if (!this.isDMing(c)) return false;
      } else if (this.activeFilter === 'playing') {
        if (this.isDMing(c)) return false;
      }

      // Search filter
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase().trim();
        const titleMatch = (c.title || '').toLowerCase().includes(query);
        const descMatch = (c.description || '').toLowerCase().includes(query);
        const settingMatch = (c.setting || '').toLowerCase().includes(query);
        const dmMatch = (c.dm_name || c.owner_id || '').toLowerCase().includes(query);
        if (!titleMatch && !descMatch && !settingMatch && !dmMatch) {
          return false;
        }
      }

      return true;
    });
  }

  private handleFilterChange(filter: RoleFilter): void {
    this.activeFilter = filter;
    this.dispatchEvent(new CustomEvent('filter-changed', {
      detail: { filter },
      bubbles: true,
      composed: true,
    }));
  }

  private handleSearchInput(e: Event): void {
    this.searchQuery = (e.target as HTMLInputElement).value;
    this.dispatchEvent(new CustomEvent('search-changed', {
      detail: { query: this.searchQuery },
      bubbles: true,
      composed: true,
    }));
  }

  private handleCardClick(campaign: CampaignItem): void {
    this.dispatchEvent(
      new CustomEvent<SelectCampaignEventDetail>('select-campaign', {
        detail: { campaignId: campaign.id, campaign },
        bubbles: true,
        composed: true,
      })
    );
  }

  public openCreator(): void {
    this.isCreatorOpen = true;
    this.dispatchEvent(new CustomEvent('open-creator', { bubbles: true, composed: true }));
  }

  public closeCreator(): void {
    this.isCreatorOpen = false;
  }

  private handleCreatorSubmit(e: CustomEvent<CreateCampaignPayload>): void {
    e.stopPropagation();
    this.isCreatorOpen = false;
    this.dispatchEvent(
      new CustomEvent<CreateCampaignPayload>('create-campaign', {
        detail: e.detail,
        bubbles: true,
        composed: true,
      })
    );
  }

  private getRoleBadgeClass(role?: string): string {
    const r = (role || '').toLowerCase();
    if (r === 'owner' || r === 'dungeon_master' || r === 'dm') return 'role-dm';
    if (r === 'player') return 'role-player';
    if (r === 'spectator') return 'role-spectator';
    return 'role-player';
  }

  private getRoleBadgeLabel(role?: string): string {
    const r = (role || '').toLowerCase();
    if (r === 'owner') return 'Owner';
    if (r === 'dungeon_master' || r === 'dm') return 'DM';
    if (r === 'player') return 'Player';
    if (r === 'spectator') return 'Spectator';
    return role || 'Member';
  }

  private renderCampaignCard(campaign: CampaignItem) {
    const hasLiveSession = campaign.has_active_session || Boolean(campaign.active_session_id);
    const playerCount = campaign.player_count ?? campaign.member_count ?? 1;
    const dmName = campaign.dm_name || (campaign.owner_id ? `DM (${campaign.owner_id})` : 'Dungeon Master');

    return html`
      <div
        class="campaign-card"
        @click=${() => this.handleCardClick(campaign)}
        role="button"
        tabindex="0"
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.handleCardClick(campaign);
          }
        }}
        data-campaign-id=${campaign.id}
      >
        <div>
          <div class="card-top">
            <h3 class="card-title">${campaign.title}</h3>
            <div class="badges-row">
              ${hasLiveSession
                ? html`<span class="badge-live"><span class="live-dot"></span>● Session Live</span>`
                : ''}
              ${campaign.role
                ? html`<span class="badge-role ${this.getRoleBadgeClass(campaign.role)}">
                    ${this.getRoleBadgeLabel(campaign.role)}
                  </span>`
                : ''}
            </div>
          </div>

          ${campaign.setting || campaign.system
            ? html`
                <div class="card-meta-line">
                  ${campaign.system ? html`<span class="meta-tag">${campaign.system}</span>` : ''}
                  ${campaign.setting ? html`<span>${campaign.setting}</span>` : ''}
                </div>
              `
            : ''}

          <p class="card-desc">
            ${campaign.description || 'No campaign description provided.'}
          </p>
        </div>

        <div class="card-footer">
          <span class="dm-info">👑 ${dmName}</span>
          <span class="player-info">👥 ${playerCount} ${playerCount === 1 ? 'Player' : 'Players'}</span>
        </div>
      </div>
    `;
  }

  render() {
    const filtered = this.filteredCampaigns;
    const creatorVisible = this.showCreator || this.isCreatorOpen;

    return html`
      <div class="campaign-dashboard">
        <header class="dashboard-header">
          <div class="header-titles">
            <h1 class="dashboard-title">Campaign Dashboard</h1>
            <p class="dashboard-subtitle">Manage your tabletop realms and active adventures</p>
          </div>
          <button
            class="btn-create-campaign"
            @click=${this.openCreator}
            type="button"
          >
            + Create Campaign
          </button>
        </header>

        <section class="controls-bar" aria-label="Campaign filters">
          <div class="filter-group" role="tablist">
            <button
              class="filter-chip ${this.activeFilter === 'all' ? 'active' : ''}"
              @click=${() => this.handleFilterChange('all')}
              type="button"
              role="tab"
              aria-selected=${this.activeFilter === 'all'}
            >
              All
            </button>
            <button
              class="filter-chip ${this.activeFilter === 'dming' ? 'active' : ''}"
              @click=${() => this.handleFilterChange('dming')}
              type="button"
              role="tab"
              aria-selected=${this.activeFilter === 'dming'}
            >
              DMing
            </button>
            <button
              class="filter-chip ${this.activeFilter === 'playing' ? 'active' : ''}"
              @click=${() => this.handleFilterChange('playing')}
              type="button"
              role="tab"
              aria-selected=${this.activeFilter === 'playing'}
            >
              Playing
            </button>
          </div>

          <div class="search-wrapper">
            <input
              type="search"
              class="search-input"
              placeholder="Search campaigns..."
              .value=${this.searchQuery}
              @input=${this.handleSearchInput}
              aria-label="Search campaigns"
            />
          </div>
        </section>

        <main class="campaigns-grid" role="region" aria-label="Campaigns list">
          ${filtered.length > 0
            ? filtered.map((c) => this.renderCampaignCard(c))
            : html`
                <div class="empty-state">
                  <div class="empty-icon">🎲</div>
                  <h3 class="empty-title">
                    ${this.campaigns.length === 0
                      ? 'No campaigns yet'
                      : 'No matching campaigns'}
                  </h3>
                  <p class="empty-desc">
                    ${this.campaigns.length === 0
                      ? 'Create your first campaign and assemble your party to begin your quest!'
                      : 'Try adjusting your search terms or role filters to find what you are looking for.'}
                  </p>
                  ${this.campaigns.length === 0
                    ? html`
                        <button
                          class="btn-create-campaign"
                          @click=${this.openCreator}
                          type="button"
                        >
                          + Create Campaign
                        </button>
                      `
                    : ''}
                </div>
              `}
        </main>

        <runefoble-campaign-creator
          .open=${creatorVisible}
          @close=${this.closeCreator}
          @cancel=${this.closeCreator}
          @create-campaign=${this.handleCreatorSubmit}
        ></runefoble-campaign-creator>
      </div>
    `;
  }
}
