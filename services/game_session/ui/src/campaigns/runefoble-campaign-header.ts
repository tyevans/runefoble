import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignHeaderStyles } from './runefoble-campaign-header.styles.ts';
import { type CampaignItem, type UpdateCampaignPayload, formatRulesetSystem } from './types.ts';

@customElement('runefoble-campaign-header')
export class RunefobleCampaignHeader extends LitElement {
  static styles = campaignHeaderStyles;

  @property({ type: Object }) campaign: CampaignItem | null = null;
  @property({ type: Boolean, attribute: 'can-manage' }) canManage = false;
  @property({ type: String, attribute: 'current-user-id' }) currentUserId = '';

  @state() isEditModalOpen = false;
  @state() editTitle = '';
  @state() editSetting = '';
  @state() editSystem = '5e';
  @state() editCoverImageUrl = '';
  @state() editDescription = '';
  @state() errorMessage = '';

  public openEditModal(): void {
    this.editTitle = this.campaign?.title || '';
    this.editSetting = this.campaign?.setting || '';
    this.editSystem = this.campaign?.system || '5e';
    this.editCoverImageUrl = this.campaign?.cover_image_url || '';
    this.editDescription = this.campaign?.description || '';
    this.errorMessage = '';
    this.isEditModalOpen = true;
  }

  public closeEditModal(): void {
    this.isEditModalOpen = false;
    this.errorMessage = '';
  }

  private handleBackdropClick(e: MouseEvent): void {
    if (e.target === e.currentTarget) this.closeEditModal();
  }

  private handleEditSubmit(e: Event): void {
    e.preventDefault();
    const trimmedTitle = this.editTitle.trim();
    if (!trimmedTitle) {
      this.errorMessage = 'Campaign title is required.';
      return;
    }
    const payload: UpdateCampaignPayload = {
      campaignId: this.campaign?.id || '',
      title: trimmedTitle,
      setting: this.editSetting.trim() || undefined,
      system: this.editSystem || '5e',
      cover_image_url: this.editCoverImageUrl.trim() || undefined,
      description: this.editDescription.trim() || undefined,
    };
    this.dispatchEvent(new CustomEvent<UpdateCampaignPayload>('update-campaign', {
      detail: payload,
      bubbles: true,
      composed: true,
    }));
    this.closeEditModal();
  }

  private renderHeroBanner() {
    if (this.campaign?.cover_image_url) {
      return html`
        <div class="hero-banner">
          <img class="cover-image" src=${this.campaign.cover_image_url} alt="${this.campaign.title || 'Campaign'} cover" loading="lazy" />
        </div>
      `;
    }
    return html`
      <div class="hero-banner hero-banner-fallback">
        <div class="geometric-pattern" aria-hidden="true"></div>
        <div class="geometric-accent-circle" aria-hidden="true"></div>
        <div class="geometric-accent-bar" aria-hidden="true"></div>
        <span class="fallback-hero-title">${this.campaign?.title || 'Tabletop Realm'}</span>
      </div>
    `;
  }

  private renderBadges() {
    const systemLabel = formatRulesetSystem(this.campaign?.system);
    const hasLiveSession = Boolean(this.campaign?.has_active_session || this.campaign?.active_session_id);
    const statusLabel = hasLiveSession ? 'Session Live' : (this.campaign?.status || 'Active');
    const isStatusActive = hasLiveSession || (this.campaign?.status || '').toLowerCase() === 'active';
    const dmName = this.campaign?.dm_name || (this.campaign?.owner_id ? `DM (${this.campaign.owner_id})` : 'Dungeon Master');
    const dmInitial = (dmName.replace(/^DM\s*\(?/, '')[0] || 'D').toUpperCase();

    return html`
      <div class="meta-badges-row">
        <span class="badge badge-system" title="Ruleset System">${systemLabel}</span>
        ${this.campaign?.setting ? html`<span class="badge badge-setting" title="Setting">🗺️ ${this.campaign.setting}</span>` : ''}
        <span class="badge badge-status ${isStatusActive ? 'status-active' : ''}" title="Campaign Status">
          <span class="status-dot"></span>${statusLabel}
        </span>
        <div class="badge-dm-profile" title="Game Master">
          <span class="dm-avatar" aria-hidden="true">${dmInitial}</span>
          <span class="dm-name">${dmName}</span>
          <span class="dm-role-tag">GM</span>
        </div>
      </div>
    `;
  }

  private renderEditModal() {
    if (!this.isEditModalOpen) return html``;
    return html`
      <div class="modal-backdrop" @click=${this.handleBackdropClick} role="dialog" aria-modal="true" aria-labelledby="edit-campaign-title-label">
        <div class="modal-card">
          <div class="modal-header">
            <h2 class="modal-title" id="edit-campaign-title-label">Edit Campaign</h2>
            <button class="btn-close" @click=${this.closeEditModal} aria-label="Close dialog" type="button">✕</button>
          </div>
          ${this.errorMessage ? html`<div class="error-banner" role="alert">⚠️ ${this.errorMessage}</div>` : ''}
          <form @submit=${this.handleEditSubmit}>
            <div class="form-group">
              <label class="form-label" for="edit-campaign-title">Campaign Title <span class="required-star">*</span></label>
              <input id="edit-campaign-title" name="title" class="form-input" type="text" placeholder="e.g. Shadows of Drakkenheim" .value=${this.editTitle} @input=${(e: Event) => { this.editTitle = (e.target as HTMLInputElement).value; this.errorMessage = ''; }} required maxlength="100" />
            </div>
            <div class="form-group">
              <label class="form-label" for="edit-campaign-setting">Setting Synopsis</label>
              <input id="edit-campaign-setting" name="setting" class="form-input" type="text" placeholder="e.g. Gothic Fantasy, Grimdark" .value=${this.editSetting} @input=${(e: Event) => (this.editSetting = (e.target as HTMLInputElement).value)} />
            </div>
            <div class="form-group">
              <label class="form-label" for="edit-campaign-system">Ruleset System</label>
              <select id="edit-campaign-system" name="system" class="form-select" .value=${this.editSystem} @change=${(e: Event) => (this.editSystem = (e.target as HTMLSelectElement).value)}>
                <option value="5e">SRD 5e (Fifth Edition)</option>
                <option value="pf2e">Pathfinder 2e</option>
                <option value="daggerheart">Daggerheart</option>
                <option value="call_of_cthulhu">Call of Cthulhu</option>
                <option value="custom">Custom Ruleset</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="edit-campaign-cover">Cover Art URL</label>
              <input id="edit-campaign-cover" name="coverImageUrl" class="form-input" type="url" placeholder="https://example.com/banner.png" .value=${this.editCoverImageUrl} @input=${(e: Event) => (this.editCoverImageUrl = (e.target as HTMLInputElement).value)} />
            </div>
            <div class="form-group">
              <label class="form-label" for="edit-campaign-description">Description / Campaign Summary</label>
              <textarea id="edit-campaign-description" name="description" class="form-textarea" placeholder="Write a brief pitch or introductory lore..." .value=${this.editDescription} @input=${(e: Event) => (this.editDescription = (e.target as HTMLTextAreaElement).value)}></textarea>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-cancel" @click=${this.closeEditModal}>Cancel</button>
              <button type="submit" class="btn-submit">Save Changes</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="campaign-header-card">
        ${this.renderHeroBanner()}
        <div class="header-content">
          ${this.renderBadges()}
          <div class="title-action-row">
            <h1 class="campaign-title">${this.campaign?.title || 'Untitled Campaign'}</h1>
            ${this.canManage
              ? html`<button class="btn-edit-campaign" @click=${this.openEditModal} type="button" aria-label="Edit campaign details">✎ Edit Campaign</button>`
              : ''}
          </div>
          <div class="campaign-description">
            ${this.campaign?.description
              ? html`<p>${this.campaign.description}</p>`
              : html`<p class="campaign-description-empty">No campaign description provided.</p>`}
          </div>
        </div>
        ${this.renderEditModal()}
      </div>
    `;
  }
}
