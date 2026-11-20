import { LitElement, html, type PropertyValues } from 'lit';
import { AssetImageSet, AuthConsumerController } from '@runefoble/ui-core';
import { customElement, property, state } from 'lit/decorators.js';
import { campaignMembersStyles } from './runefoble-campaign-members.styles.ts';
import {
  ROLE_LABELS,
  isDungeonMasterRole,
  isOwnerRole,
  isPlayerRole,
  isSpectatorRole,
  normalizeRole,
} from '../lobby/roles.ts';
import type {
  CampaignMember,
  AssignRoleEventDetail,
  RemoveMemberEventDetail,
  CreateInviteEventDetail,
} from './types.ts';

@customElement('runefoble-campaign-members')
export class RunefobleCampaignMembers extends LitElement {
  private readonly auth = new AuthConsumerController(this);
  /** Member avatars by user id. Protected asset paths load with the bearer (TASK-0785). */
  private readonly avatars = new AssetImageSet(this, () => this.auth.authHeaders());

  override willUpdate(changed: PropertyValues) {
    super.willUpdate(changed);
    for (const member of this.members) {
      this.avatars.setSource(member.user_id, member.avatar_url ?? '');
    }
    this.avatars.retain(this.members.map((member) => member.user_id));
  }

  static styles = campaignMembersStyles;

  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: String, attribute: 'campaign-title' }) campaignTitle = '';
  @property({ type: Array }) members: CampaignMember[] = [];
  /** Server permission flag (`manage` on the campaign). Set by the App Shell from the capabilities route. */
  @property({ type: Boolean, attribute: 'can-manage' }) canManage = false;
  @property({ type: String, attribute: 'current-user-id' }) currentUserId = '';
  /** The full invite URL from the App Shell, or an empty string before the DM generates a link (ADR-0015). */
  @property({ type: String, attribute: 'invite-url' }) inviteUrl = '';

  @state() private isInviteOpen = false;
  @state() private selectedInviteRole: 'player' | 'spectator' = 'player';
  @state() private memberToRemove: CampaignMember | null = null;
  /** The result of the last copy. It is `copied` only after the clipboard accepts the link. */
  @state() private copyState: 'idle' | 'copied' | 'failed' = 'idle';

  private formatRole(role: string): string {
    const known = normalizeRole(role);
    return known === 'unknown' ? role : ROLE_LABELS[known];
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
    this.copyState = 'idle';
  }

  public closeInviteModal(): void {
    this.isInviteOpen = false;
    this.copyState = 'idle';
  }

  private handleGenerateInvite(): void {
    this.dispatchEvent(new CustomEvent<CreateInviteEventDetail>('create-invite', {
      detail: { campaignId: this.campaignId, role: this.selectedInviteRole },
      bubbles: true,
      composed: true,
    }));
  }

  private async copyInviteLink(): Promise<void> {
    const link = this.inviteUrl;
    try {
      if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(link);
    } catch {
      this.copyState = 'failed';
      return;
    }
    this.copyState = 'copied';
    this.dispatchEvent(new CustomEvent('copy-invite-link', {
      detail: { inviteUrl: link, role: this.selectedInviteRole },
      bubbles: true,
      composed: true,
    }));
    setTimeout(() => { if (this.copyState === 'copied') this.copyState = 'idle'; }, 2000);
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
      return html`<div class="avatar"><img src=${this.avatars.url(member.user_id)} alt=${member.username} /></div>`;
    }
    const initial = (member.username || member.user_id || '?').charAt(0).toUpperCase();
    return html`<div class="avatar">${initial}</div>`;
  }

  private renderMemberItem(member: CampaignMember) {
    const isOwner = isOwnerRole(member.role);
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
          ${isOwner ? html`<span class="badge-role role-owner">Owner</span>` : this.canManage ? html`
            <select class="role-select" @change=${(e: Event) => this.handleRoleSelect(member, e)} aria-label="Assign role">
              <option value="player" ?selected=${isPlayerRole(member.role)}>Player</option>
              <option value="dungeon_master" ?selected=${isDungeonMasterRole(member.role)}>Dungeon Master</option>
              <option value="spectator" ?selected=${isSpectatorRole(member.role)}>Spectator</option>
            </select>
          ` : html`<span class="badge-role role-${member.role}">${this.formatRole(member.role)}</span>`}
          ${this.canManage && !isOwner && !isSelf ? html`
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
          ${this.inviteUrl ? html`
            <div class="form-group">
              <label class="form-label">Shareable Link</label>
              <div class="invite-link-row">
                <input type="text" class="form-input invite-link-input" readonly .value=${this.inviteUrl} />
                <button class="btn-copy" @click=${this.copyInviteLink} type="button">
                  ${this.copyState === 'copied' ? 'Copied!' : 'Copy Link'}
                </button>
              </div>
              ${this.copyState === 'copied' ? html`<span class="copied-badge">✓ Copied to clipboard!</span>` : ''}
              ${this.copyState === 'failed' ? html`<span class="copy-failed-badge" role="alert">Copy failed. Select the link and copy it.</span>` : ''}
            </div>
          ` : ''}
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
            ${this.canManage ? html`<button class="btn-invite" @click=${this.openInviteModal} type="button" aria-label="Invite Adventurers">+ Invite Adventurers</button>` : ''}
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
