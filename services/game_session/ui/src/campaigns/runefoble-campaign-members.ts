import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignMembersStyles } from './runefoble-campaign-members.styles.ts';
import type {
  CampaignMember,
  AssignRoleEventDetail,
  RemoveMemberEventDetail,
  CreateInviteEventDetail,
} from './types.ts';

@customElement('runefoble-campaign-members')
export class RunefobleCampaignMembers extends LitElement {
  static styles = campaignMembersStyles;

  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: String, attribute: 'campaign-title' }) campaignTitle = '';
  @property({ type: Array }) members: CampaignMember[] = [];
  @property({ type: Boolean, attribute: 'can-manage' }) canManage = false;
  @property({ type: Boolean, attribute: 'is-gm' }) isGm = false;
  @property({ type: String, attribute: 'current-user-id' }) currentUserId = '';
  @property({ type: String, attribute: 'invite-url' }) inviteUrl = '';
  @property({ type: String, attribute: 'invite-token' }) inviteToken = '';

  @state() private isInviteOpen = false;
  @state() private selectedInviteRole: 'player' | 'spectator' = 'player';
  @state() private memberToRemove: CampaignMember | null = null;
  @state() private copied = false;

  get isManager(): boolean {
    return this.canManage || this.isGm;
  }

  get effectiveInviteUrl(): string {
    if (this.inviteUrl) return this.inviteUrl;
    const token = this.inviteToken || 'sample_token';
    const origin = typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin
      : 'https://runefoble.local';
    return `${origin}/#/join/${token}`;
  }

  private formatRole(role: string): string {
    const map: Record<string, string> = {
      owner: 'Owner',
      dungeon_master: 'Dungeon Master',
      dm: 'Dungeon Master',
      player: 'Player',
      spectator: 'Spectator',
    };
    return map[(role || '').toLowerCase()] || role;
  }

  private handleRoleSelect(member: CampaignMember, e: Event): void {
    const role = (e.target as HTMLSelectElement).value;
    this.dispatchEvent(new CustomEvent<AssignRoleEventDetail>('assign-role', {
      detail: { campaignId: this.campaignId, userId: member.user_id, role },
      bubbles: true,
      composed: true,
    }));
  }

  public openInviteModal(): void {
    this.isInviteOpen = true;
    this.copied = false;
  }

  public closeInviteModal(): void {
    this.isInviteOpen = false;
    this.copied = false;
  }

  private handleGenerateInvite(): void {
    this.dispatchEvent(new CustomEvent<CreateInviteEventDetail>('create-invite', {
      detail: { campaignId: this.campaignId, role: this.selectedInviteRole },
      bubbles: true,
      composed: true,
    }));
  }

  private async copyInviteLink(): Promise<void> {
    const link = this.effectiveInviteUrl;
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(link).catch(() => {});
    }
    if (typeof window !== 'undefined') {
      (window as any).__lastCopiedInviteUrl = link;
    }
    this.copied = true;
    this.dispatchEvent(new CustomEvent('copy-invite-link', {
      detail: { inviteUrl: link, role: this.selectedInviteRole },
      bubbles: true,
      composed: true,
    }));
    setTimeout(() => { this.copied = false; }, 2000);
  }

  private confirmRemove(): void {
    if (!this.memberToRemove) return;
    const userId = this.memberToRemove.user_id;
    this.memberToRemove = null;
    this.dispatchEvent(new CustomEvent<RemoveMemberEventDetail>('remove-member', {
      detail: { campaignId: this.campaignId, userId },
      bubbles: true,
      composed: true,
    }));
  }

  private renderAvatar(member: CampaignMember) {
    if (member.avatar_url) {
      return html`<div class="avatar"><img src=${member.avatar_url} alt=${member.username} /></div>`;
    }
    const initial = (member.username || member.user_id || '?').charAt(0).toUpperCase();
    return html`<div class="avatar">${initial}</div>`;
  }

  private renderMemberItem(member: CampaignMember) {
    const isOwner = member.role === 'owner';
    const isSelf = this.currentUserId && member.user_id === this.currentUserId;

    return html`
      <div class="member-item" data-user-id=${member.user_id}>
        <div class="member-profile">
          ${this.renderAvatar(member)}
          <div class="member-details">
            <div class="member-name-row">
              <span class="username">${member.username || member.user_id}</span>
              ${member.character_name ? html`<span class="character-tag">⚔️ ${member.character_name}</span>` : ''}
            </div>
            <span class="user-id-tag">ID: ${member.user_id}</span>
          </div>
        </div>
        <div class="member-controls">
          ${isOwner ? html`<span class="badge-role role-owner">Owner</span>` : this.isManager ? html`
            <select class="role-select" @change=${(e: Event) => this.handleRoleSelect(member, e)} aria-label="Assign role">
              <option value="player" ?selected=${member.role === 'player'}>Player</option>
              <option value="dungeon_master" ?selected=${member.role === 'dungeon_master' || member.role === 'dm'}>Dungeon Master</option>
              <option value="spectator" ?selected=${member.role === 'spectator'}>Spectator</option>
            </select>
          ` : html`<span class="badge-role role-${member.role}">${this.formatRole(member.role)}</span>`}
          ${this.isManager && !isOwner && !isSelf ? html`
            <button class="btn-remove" @click=${() => { this.memberToRemove = member; }} type="button">Remove</button>
          ` : ''}
        </div>
      </div>
    `;
  }

  private renderInviteModal() {
    if (!this.isInviteOpen) return '';
    return html`
      <div class="modal-backdrop" @click=${this.closeInviteModal}>
        <div class="modal-card" @click=${(e: Event) => e.stopPropagation()}>
          <div class="modal-header">
            <h3 class="modal-title">Invite Player to Campaign</h3>
            <button class="btn-close" @click=${this.closeInviteModal} type="button">×</button>
          </div>
          <div class="form-group">
            <label class="form-label" for="invite-role-select">Zanzibar Role Pre-Assignment</label>
            <div class="invite-role-row" style="display: flex; gap: 8px;">
              <select id="invite-role-select" class="form-select" style="flex: 1;" .value=${this.selectedInviteRole}
                @change=${(e: Event) => {
                  this.selectedInviteRole = (e.target as HTMLSelectElement).value as 'player' | 'spectator';
                  this.handleGenerateInvite();
                }}>
                <option value="player">Player</option>
                <option value="spectator">Spectator</option>
              </select>
              <button class="btn-generate-link" @click=${this.handleGenerateInvite} type="button">Generate Link</button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Shareable Link</label>
            <div class="invite-link-row">
              <input type="text" class="form-input invite-link-input" readonly .value=${this.effectiveInviteUrl} />
              <button class="btn-copy" @click=${this.copyInviteLink} type="button">
                ${this.copied ? 'Copied!' : 'Copy Link'}
              </button>
            </div>
            ${this.copied ? html`<span class="copied-badge">✓ Copied to clipboard!</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }

  private renderConfirmModal() {
    if (!this.memberToRemove) return '';
    const name = this.memberToRemove.username || this.memberToRemove.user_id;
    return html`
      <div class="modal-backdrop" @click=${() => { this.memberToRemove = null; }}>
        <div class="modal-card" @click=${(e: Event) => e.stopPropagation()}>
          <div class="modal-header">
            <h3 class="modal-title">Remove Member</h3>
            <button class="btn-close" @click=${() => { this.memberToRemove = null; }} type="button">×</button>
          </div>
          <p class="modal-desc">Are you sure you want to remove <strong>${name}</strong> from this campaign?</p>
          <div class="modal-actions">
            <button class="btn-cancel" @click=${() => { this.memberToRemove = null; }} type="button">Cancel</button>
            <button class="btn-confirm-remove" @click=${this.confirmRemove} type="button">Confirm Remove</button>
          </div>
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="members-container">
        <header class="members-header">
          <div class="header-left">
            <h2 class="members-title">Campaign Roster & Roles</h2>
            <p class="members-subtitle">${this.campaignTitle ? `${this.campaignTitle} • ` : ''}Manage player permissions and SpiceDB Zanzibar relations</p>
          </div>
          <div class="header-actions">
            ${this.isManager ? html`<button class="btn-invite" @click=${this.openInviteModal} type="button" aria-label="Invite Adventurers">+ Invite Adventurers</button>` : ''}
          </div>
        </header>

        <div class="roster-card">
          ${this.members.length > 0 ? html`<div class="roster-list">${this.members.map((m) => this.renderMemberItem(m))}</div>` : html`
            <div class="empty-state">
              <div class="empty-icon">🛡️</div>
              <h3 class="empty-title">No members in campaign</h3>
              <p class="empty-desc">Generate an invite link to invite party members and assign Zanzibar roles.</p>
            </div>
          `}
        </div>

        ${this.renderInviteModal()}
        ${this.renderConfirmModal()}
      </div>
    `;
  }
}
