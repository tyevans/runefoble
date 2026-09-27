import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { characterRosterStyles } from './runefoble-character-roster.styles.ts';
import './runefoble-character-builder-modal.ts';
import {
  type CharacterItem,
  type RosterCampaignOption,
  type CreateCharacterPayload,
  type AssignCampaignEventDetail,
  type InspectCharacterEventDetail,
  type DeleteCharacterEventDetail,
  filterCharacters,
} from './types.ts';

@customElement('runefoble-character-roster')
export class RunefobleCharacterRoster extends LitElement {
  static styles = [characterRosterStyles];

  @property({ type: Array }) characters: CharacterItem[] = [];
  @property({ type: Array }) campaigns: RosterCampaignOption[] = [];
  @property({ type: String, attribute: 'current-user-id' }) currentUserId = '';
  @property({ type: String, attribute: 'active-filter' }) activeFilter: 'all' | 'assigned' | 'unassigned' = 'all';

  @state() private searchQuery = '';
  @state() private isBuilderOpen = false;
  @state() private isAssignModalOpen = false;
  @state() private characterToAssign: CharacterItem | null = null;
  @state() private selectedCampaignId = '';
  @state() private characterToDelete: CharacterItem | null = null;

  get filteredList(): CharacterItem[] {
    return filterCharacters(this.characters, this.searchQuery, this.activeFilter);
  }

  private handleInspect(character: CharacterItem) {
    this.dispatchEvent(new CustomEvent<InspectCharacterEventDetail>('inspect-character', {
      detail: { characterId: character.id, character },
      bubbles: true,
      composed: true,
    }));
  }

  private handleOpenAssign(character: CharacterItem) {
    this.characterToAssign = character;
    this.selectedCampaignId = character.campaignId || '';
    this.isAssignModalOpen = true;
  }

  private handleConfirmAssign() {
    if (!this.characterToAssign) return;
    const camp = this.campaigns.find((c) => c.id === this.selectedCampaignId);
    this.dispatchEvent(new CustomEvent<AssignCampaignEventDetail>('assign-campaign', {
      detail: {
        characterId: this.characterToAssign.id,
        campaignId: this.selectedCampaignId || null,
        campaignTitle: camp ? camp.title : null,
      },
      bubbles: true,
      composed: true,
    }));
    this.isAssignModalOpen = false;
    this.characterToAssign = null;
  }

  private handleConfirmDelete() {
    if (!this.characterToDelete) return;
    this.dispatchEvent(new CustomEvent<DeleteCharacterEventDetail>('delete-character', {
      detail: { characterId: this.characterToDelete.id },
      bubbles: true,
      composed: true,
    }));
    this.characterToDelete = null;
  }

  private handleCharacterCreated(e: CustomEvent<CreateCharacterPayload>) {
    this.dispatchEvent(new CustomEvent<CreateCharacterPayload>('create-character', {
      detail: e.detail,
      bubbles: true,
      composed: true,
    }));
    this.isBuilderOpen = false;
  }

  private renderCard(char: CharacterItem) {
    const hpPct = Math.max(0, Math.min(100, Math.round((char.currentHp / (char.maxHp || 1)) * 100)));
    const isLowHp = hpPct <= 30;
    return html`
      <article class="character-card" data-character-id=${char.id}>
        <div class="card-top">
          <img class="avatar-thumb" src=${char.portraitUrl || '/assets/portraits/default.svg'} alt=${char.name} />
          <div class="card-identity">
            <h3 class="card-name" title=${char.name}>${char.name}</h3>
            <div class="card-class">
              ${char.characterClass}${char.subclass ? ` (${char.subclass})` : ''}
            </div>
          </div>
          <span class="card-level-badge">Lvl ${char.level}</span>
        </div>

        <div class="vitals-row">
          <div class="hp-header">
            <span>HP</span>
            <span>${char.currentHp} / ${char.maxHp}</span>
          </div>
          <div class="hp-bar-bg">
            <div class="hp-bar-fill ${isLowHp ? 'low' : ''}" style="width: ${hpPct}%"></div>
          </div>
        </div>

        <div class="stats-row">
          <div class="stat-chip">🛡️ AC ${char.armorClass}</div>
          <div class="stat-chip">⚡ ${char.speed || 30} ft</div>
        </div>

        <div class="campaign-badge ${char.campaignId ? 'linked' : 'unassigned'}">
          ${char.campaignId
            ? html`<span>🏰</span><span>${char.campaignTitle || `Campaign #${char.campaignId}`}</span>`
            : html`<span>○</span><span>Unassigned</span>`}
        </div>

        <div class="card-actions">
          <button class="btn btn-secondary" @click=${() => this.handleInspect(char)}>Inspect Sheet</button>
          <button class="btn btn-secondary" @click=${() => this.handleOpenAssign(char)}>Assign to Campaign</button>
          <button class="btn btn-danger" @click=${() => { this.characterToDelete = char; }}>Delete</button>
        </div>
      </article>
    `;
  }

  render() {
    const list = this.filteredList;
    return html`
      <div class="roster-container">
        <header class="roster-header">
          <div class="title-group">
            <h1>Character Roster</h1>
            <p>Manage your adventurers and active campaign party assignments</p>
          </div>
          <button id="create-char-btn" class="btn btn-primary" @click=${() => { this.isBuilderOpen = true; }}>
            <span>+</span> Create Character
          </button>
        </header>

        <section class="controls-bar">
          <input
            type="search"
            class="search-input"
            placeholder="Search characters by name, class..."
            .value=${this.searchQuery}
            @input=${(e: Event) => { this.searchQuery = (e.target as HTMLInputElement).value; }}
          />
          <div class="filter-pills">
            <button
              class="filter-pill ${this.activeFilter === 'all' ? 'active' : ''}"
              @click=${() => { this.activeFilter = 'all'; }}
            >All (${this.characters.length})</button>
            <button
              class="filter-pill ${this.activeFilter === 'assigned' ? 'active' : ''}"
              @click=${() => { this.activeFilter = 'assigned'; }}
            >Assigned</button>
            <button
              class="filter-pill ${this.activeFilter === 'unassigned' ? 'active' : ''}"
              @click=${() => { this.activeFilter = 'unassigned'; }}
            >Unassigned</button>
          </div>
        </section>

        <main class="character-grid">
          ${list.length > 0
            ? list.map((c) => this.renderCard(c))
            : html`
                <div class="empty-roster">
                  <div class="empty-icon">⚔️</div>
                  <h3>No characters found</h3>
                  <p>Create your first adventurer to embark on epic quests.</p>
                  <button class="btn btn-primary" @click=${() => { this.isBuilderOpen = true; }}>
                    Build Your First Character
                  </button>
                </div>
              `}
        </main>

        ${this.isAssignModalOpen && this.characterToAssign ? html`
          <div class="modal-backdrop" @click=${(e: MouseEvent) => { if (e.target === e.currentTarget) this.isAssignModalOpen = false; }}>
            <div class="assign-dialog" role="dialog" aria-modal="true" aria-labelledby="assign-title">
              <h2 id="assign-title" class="dialog-title">Assign to Campaign</h2>
              <p>Assign <strong>${this.characterToAssign.name}</strong> to an active campaign party:</p>
              <select
                class="dialog-select"
                .value=${this.selectedCampaignId}
                @change=${(e: Event) => { this.selectedCampaignId = (e.target as HTMLSelectElement).value; }}
              >
                <option value="">None (Unassign from Campaign)</option>
                ${this.campaigns.map((camp) => html`
                  <option value=${camp.id}>${camp.title} (#${camp.id})</option>
                `)}
              </select>
              <div class="dialog-footer">
                <button class="btn btn-secondary" @click=${() => { this.isAssignModalOpen = false; }}>Cancel</button>
                <button class="btn btn-primary" @click=${this.handleConfirmAssign}>Confirm Assignment</button>
              </div>
            </div>
          </div>
        ` : ''}

        ${this.characterToDelete ? html`
          <div class="modal-backdrop" @click=${(e: MouseEvent) => { if (e.target === e.currentTarget) this.characterToDelete = null; }}>
            <div class="assign-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-title">
              <h2 id="delete-title" class="dialog-title">Delete Character</h2>
              <p>Are you sure you want to delete <strong>${this.characterToDelete.name}</strong>? This action cannot be undone.</p>
              <div class="dialog-footer">
                <button class="btn btn-secondary" @click=${() => { this.characterToDelete = null; }}>Cancel</button>
                <button class="btn btn-danger" @click=${this.handleConfirmDelete}>Confirm Delete</button>
              </div>
            </div>
          </div>
        ` : ''}

        <runefoble-character-builder-modal
          .open=${this.isBuilderOpen}
          @create-character=${this.handleCharacterCreated}
          @builder-close=${() => { this.isBuilderOpen = false; }}
        ></runefoble-character-builder-modal>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-character-roster': RunefobleCharacterRoster;
  }
}
