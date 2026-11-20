import { LitElement, html, type PropertyValues, type TemplateResult } from 'lit';
import { AssetImageSet, AuthConsumerController } from '@runefoble/ui-core';
import { customElement, property, state } from 'lit/decorators.js';
import { live } from 'lit/directives/live.js';
import { sessionLobbyStyles } from './runefoble-session-lobby.styles.ts';
import {
  type LobbyParticipant,
  type LobbyCharacterOption,
  type ReadinessSummary,
  type SelectCharacterEventDetail,
  type ToggleReadinessEventDetail,
  type ToggleStandInEventDetail,
  type LaunchSessionEventDetail,
  type TakeSeatEventDetail,
  computeReadinessSummary,
} from './types.ts';
import { canTakeSeat } from './seat.ts';

/** Row key of one participant image. Avatar and portrait are separate rows. */
const imageKey = (userId: string, slot: 'avatar' | 'portrait') => `${userId}:${slot}`;

/** The count the DM sees before launch. The launch rule does not wait for it (TASK-0952). */
const seatsNotReadyText = (count: number) => `${count} ${count === 1 ? 'seat' : 'seats'} not ready`;

@customElement('runefoble-session-lobby')
export class RunefobleSessionLobby extends LitElement {
  private readonly auth = new AuthConsumerController(this);
  /** Participant images. Protected asset paths load with the bearer (TASK-0785). */
  private readonly images = new AssetImageSet(this, () => this.auth.authHeaders());

  override willUpdate(changed: PropertyValues) {
    super.willUpdate(changed);
    const keys: string[] = [];
    for (const p of this.participants) {
      const avatar = imageKey(p.userId, 'avatar');
      const portrait = imageKey(p.userId, 'portrait');
      keys.push(avatar, portrait);
      this.images.setSource(avatar, p.avatarUrl ?? '');
      this.images.setSource(portrait, p.portraitUrl ?? '');
    }
    this.images.retain(keys);
  }

  static styles = sessionLobbyStyles;

  @property({ type: String, attribute: 'session-id' }) sessionId = '';
  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: String, attribute: 'session-title' }) sessionTitle = 'Session Lobby';
  @property({ type: String, attribute: 'current-user-id' }) currentUserId = '';
  @property({ type: Array }) participants: LobbyParticipant[] = [];
  @property({ type: Array }) availableCharacters: LobbyCharacterOption[] = [];
  @property({ type: Boolean, attribute: 'is-dm' }) isDm = false;
  @property({ type: Boolean, attribute: 'is-loading' }) isLoading = false;
  /** The caller holds `campaign.play` (server capability reply). */
  @property({ type: Boolean, attribute: 'can-play' }) canPlay = false;
  @state() private seatCharacterId = '';

  get canUserLaunch(): boolean {
    return this.isDm;
  }

  get canUserTakeSeat(): boolean {
    return canTakeSeat({
      canPlay: this.canPlay,
      canRunSession: this.isDm,
      currentUserId: this.currentUserId,
      participants: this.participants,
    });
  }

  get readinessSummary(): ReadinessSummary {
    return computeReadinessSummary(this.participants);
  }

  private handleLaunch(): void {
    if (!this.canUserLaunch || this.isLoading) return;
    this.dispatchEvent(new CustomEvent<LaunchSessionEventDetail>('launch-session', {
      detail: { sessionId: this.sessionId, campaignId: this.campaignId },
      bubbles: true, composed: true,
    }));
  }

  private handleTakeSeat(): void {
    const character = this.availableCharacters.find((c) => c.id === this.seatCharacterId) ?? this.availableCharacters[0];
    if (!character || this.isLoading) return;
    this.dispatchEvent(new CustomEvent<TakeSeatEventDetail>('take-seat', {
      detail: {
        sessionId: this.sessionId,
        characterId: character.id,
        characterName: character.name,
        characterClass: character.characterClass,
      },
      bubbles: true, composed: true,
    }));
  }

  private renderSeatPanel(): TemplateResult {
    if (!this.canUserTakeSeat) return html``;
    const hasCharacters = this.availableCharacters.length > 0;
    return html`
      <div class="seat-panel">
        ${hasCharacters
          ? html`
              <div class="char-select-container">
                <label class="select-label" for="seat-character-select">Your Character</label>
                <select
                  id="seat-character-select"
                  class="character-dropdown seat-character-select"
                  @change=${(e: Event) => { this.seatCharacterId = (e.target as HTMLSelectElement).value; }}
                >
                  ${this.availableCharacters.map(
                    (c) => html`<option value="${c.id}" ?selected=${c.id === this.seatCharacterId}>${c.name} (${c.characterClass} Lv ${c.level})</option>`
                  )}
                </select>
              </div>
            `
          : html`<p class="seat-hint">Create a character to take a seat.</p>`}
        <button
          class="btn-take-seat"
          ?disabled=${!hasCharacters || this.isLoading}
          @click=${this.handleTakeSeat}
        >
          Take a Seat
        </button>
      </div>
    `;
  }

  private handleSelectCharacter(userId: string, characterId: string): void {
    const character = this.availableCharacters.find((c) => c.id === characterId);
    this.dispatchEvent(new CustomEvent<SelectCharacterEventDetail>('select-character', {
      detail: { sessionId: this.sessionId, userId, characterId, character },
      bubbles: true, composed: true,
    }));
  }

  private handleToggleReadiness(userId: string, isReady: boolean): void {
    this.dispatchEvent(new CustomEvent<ToggleReadinessEventDetail>('toggle-readiness', {
      detail: { sessionId: this.sessionId, userId, isReady },
      bubbles: true, composed: true,
    }));
  }

  private handleToggleStandIn(userId: string, isAbsent: boolean): void {
    this.dispatchEvent(new CustomEvent<ToggleStandInEventDetail>('toggle-stand-in', {
      detail: { sessionId: this.sessionId, userId, isAbsent },
      bubbles: true, composed: true,
    }));
  }

  private renderAvatar(p: LobbyParticipant): TemplateResult {
    const status = p.onlineStatus || 'online';
    const initial = p.username.charAt(0).toUpperCase() || '?';
    return html`
      <div class="avatar-wrap">
        ${p.avatarUrl
          ? html`<img class="avatar-img" src="${this.images.url(imageKey(p.userId, 'avatar'))}" alt="${p.username}" />`
          : html`<div class="avatar-fallback">${initial}</div>`}
        <span class="presence-dot ${status}" title="${status}"></span>
      </div>
    `;
  }

  private renderReadinessBadge(p: LobbyParticipant): TemplateResult {
    if (p.isAbsent) {
      return html`<span class="badge-readiness badge-standin">AI Stand-In</span>`;
    }
    if (p.isReady) {
      return html`<span class="badge-readiness badge-ready">Ready</span>`;
    }
    return html`<span class="badge-readiness badge-setting-up">Setting Up</span>`;
  }

  private renderCharacterPreview(p: LobbyParticipant, isSelf: boolean): TemplateResult {
    const hasChar = Boolean(p.characterId || p.characterName);
    const initial = p.characterName ? p.characterName.charAt(0).toUpperCase() : '?';

    return html`
      <div class="character-card-preview">
        ${p.portraitUrl
          ? html`<img class="char-portrait" src="${this.images.url(imageKey(p.userId, 'portrait'))}" alt="Portrait" />`
          : html`<div class="char-portrait-fallback">${initial}</div>`}
        <div class="char-details">
          ${hasChar
            ? html`
                <span class="char-name">${p.characterName || 'Unknown Hero'}</span>
                <span class="char-meta">
                  ${p.characterClass || 'Adventurer'} ${p.characterLevel ? `• Lv ${p.characterLevel}` : ''}
                </span>
              `
            : html`<span class="no-character-msg">No character selected</span>`}
        </div>
      </div>

      ${isSelf && !p.isAbsent && this.availableCharacters.length > 0
        ? html`
            <div class="char-select-container">
              <label class="select-label" for="char-select-${p.userId}">Switch Character</label>
              <select
                id="char-select-${p.userId}"
                class="character-dropdown"
                .value=${p.characterId || ''}
                @change=${(e: Event) => this.handleSelectCharacter(p.userId, (e.target as HTMLSelectElement).value)}
              >
                <option value="">-- Choose Character --</option>
                ${this.availableCharacters.map(
                  (c) => html`
                    <option value="${c.id}" ?selected=${c.id === p.characterId}>
                      ${c.name} (${c.characterClass} Lv ${c.level})
                    </option>
                  `
                )}
              </select>
            </div>
          `
        : ''}
    `;
  }

  private renderControls(p: LobbyParticipant, isSelf: boolean): TemplateResult {
    // A player marks their own seat. The DM marks any seat (TASK-0952). The owner checks both.
    const canToggleAbsent = isSelf || this.isDm;
    const canToggleReady = isSelf && !p.isAbsent;

    if (!canToggleAbsent && !canToggleReady) return html``;

    return html`
      <div class="card-controls">
        ${canToggleReady
          ? html`
              <label class="control-toggle toggle-ready">
                <input
                  type="checkbox"
                  class="checkbox-ready"
                  .checked=${live(p.isReady)}
                  @change=${(e: Event) => this.handleToggleReadiness(p.userId, (e.target as HTMLInputElement).checked)}
                />
                Ready to Play
              </label>
            `
          : ''}
        ${canToggleAbsent
          ? html`
              <label class="control-toggle toggle-standin">
                <input
                  type="checkbox"
                  class="checkbox-absent"
                  .checked=${live(p.isAbsent)}
                  @change=${(e: Event) => this.handleToggleStandIn(p.userId, (e.target as HTMLInputElement).checked)}
                />
                Mark Absent (AI Stand-In)
              </label>
            `
          : ''}
      </div>
    `;
  }

  private renderParticipantCard(p: LobbyParticipant): TemplateResult {
    const isSelf = p.userId === this.currentUserId;
    return html`
      <div class="participant-card ${isSelf ? 'current-user' : ''} ${p.isAbsent ? 'absent' : ''}">
        <div class="card-top">
          <div class="user-identity">
            ${this.renderAvatar(p)}
            <div class="user-info">
              <span class="username">${p.username}${isSelf ? ' (You)' : ''}</span>
              <span class="user-role">${p.role}</span>
            </div>
          </div>
          ${this.renderReadinessBadge(p)}
        </div>

        ${this.renderCharacterPreview(p, isSelf)}
        ${this.renderControls(p, isSelf)}
      </div>
    `;
  }

  render(): TemplateResult {
    const summary = this.readinessSummary;

    return html`
      <div class="lobby-container">
        <header class="lobby-header">
          <div class="header-titles">
            <span class="lobby-badge-status">
              <span class="status-pulse"></span> Pre-Game Assembly
            </span>
            <h1 class="lobby-title">${this.sessionTitle}</h1>
            <p class="lobby-subtitle">Assemble party, confirm character sheets, and coordinate launch.</p>
          </div>

          <div class="header-actions">
            <div class="readiness-summary-pill" title="Current player readiness">
              <span>●</span>
              <span class="readiness-summary-text">${summary.summaryText}</span>
            </div>

            ${this.canUserLaunch && summary.notReadyCount > 0
              ? html`<span class="launch-hint">${seatsNotReadyText(summary.notReadyCount)}</span>`
              : ''}

            ${this.canUserLaunch
              ? html`
                  <button
                    class="btn-launch"
                    ?disabled=${this.isLoading}
                    @click=${this.handleLaunch}
                  >
                    🚀 Launch Session
                  </button>
                `
              : ''}
          </div>
        </header>

        <section class="participants-section">
          ${this.renderSeatPanel()}
          <div class="section-label">Party Roster (${this.participants.length} Assembled)</div>

          ${this.participants.length === 0
            ? html`
                <div class="empty-state">
                  <h3>No Adventurers Assembled</h3>
                  <p>No party members have joined yet. Open the campaign to share the invite link.</p>
                </div>
              `
            : html`
                <div class="participants-grid">
                  ${this.participants.map((p) => this.renderParticipantCard(p))}
                </div>
              `}
        </section>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-session-lobby': RunefobleSessionLobby;
  }
}
