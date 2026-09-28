import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './runefoble-session-modal.ts';
import type { CreateSessionDetail } from './runefoble-session-modal.ts';

export interface CampaignSessionItem {
  id: string;
  campaignId: string;
  title: string;
  status: 'active' | 'lobby' | 'upcoming' | 'completed';
  round?: number;
  participantsCount?: number;
  scheduledAt?: string;
  scheduled_at?: string;
  description?: string;
}

export type { CreateSessionDetail };

@customElement('runefoble-session-list')
export class RunefobleSessionList extends LitElement {
  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: Array }) sessions: CampaignSessionItem[] = [];
  @property({ type: Boolean, attribute: 'is-dm' }) isDm = false;
  @property({ type: Boolean, attribute: 'create-modal-open' }) isCreateModalOpen = false;

  static styles = css`
    :host {
      display: block;
      margin-top: 24px;
    }
    .sessions-card {
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow);
      padding: 24px;
    }
    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .title-group h3 {
      font-size: 1.3rem;
      font-weight: 800;
      margin: 0 0 4px 0;
      color: var(--rf-text-primary);
    }
    .title-group p {
      font-size: 0.85rem;
      color: var(--rf-text-muted);
      margin: 0;
    }
    .btn-create {
      background: var(--rf-bg-surface);
      color: var(--rf-text-primary);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      font-weight: 800;
      font-size: 0.85rem;
      padding: 8px 16px;
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .btn-create:hover {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow);
    }
    .sessions-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .session-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      background: var(--rf-bg-canvas);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      flex-wrap: wrap;
      gap: 12px;
    }
    .session-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .session-title-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .session-title {
      font-weight: 800;
      font-size: 1rem;
      color: var(--rf-text-primary);
    }
    .session-meta {
      font-size: 0.8rem;
      color: var(--rf-text-muted);
    }
    .session-schedule {
      color: var(--rf-accent-secondary, #1d3557);
      font-weight: 700;
    }
    .session-description {
      font-size: 0.85rem;
      color: var(--rf-text-primary);
      margin-top: 4px;
      font-style: italic;
    }
    .badge-status {
      font-size: 0.75rem;
      font-weight: 800;
      padding: 2px 8px;
      text-transform: uppercase;
      border: 1px solid var(--rf-border-color);
    }
    .badge-active {
      background: var(--rf-accent-primary, #e63946);
      color: #fff;
    }
    .badge-lobby {
      background: var(--rf-accent-secondary, #457b9d);
      color: #fff;
    }
    .badge-upcoming {
      background: var(--rf-bg-surface);
      color: var(--rf-text-primary);
    }
    .badge-completed {
      background: var(--rf-bg-inset, #e9ecef);
      color: var(--rf-text-muted, #6c757d);
    }
    .action-group {
      display: flex;
      gap: 8px;
    }
    .btn-action {
      background: var(--rf-bg-surface);
      color: var(--rf-text-primary);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      box-shadow: var(--rf-shadow-sm);
      font-weight: 700;
      font-size: 0.8rem;
      padding: 6px 12px;
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .btn-action:hover {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow);
    }
    .btn-action.primary {
      background: var(--rf-accent-primary, #e63946);
      color: #fff;
    }
    .empty-state {
      padding: 32px;
      text-align: center;
      color: var(--rf-text-muted);
      border: 2px dashed var(--rf-border-color);
    }
  `;

  public openCreateModal() {
    this.isCreateModalOpen = true;
  }

  public closeCreateModal() {
    this.isCreateModalOpen = false;
  }

  private handleEnterLobby(sessionId: string) {
    this.dispatchEvent(new CustomEvent('enter-lobby', {
      detail: { sessionId, campaignId: this.campaignId },
      bubbles: true,
      composed: true,
    }));
  }

  private handleJoinSession(sessionId: string) {
    this.dispatchEvent(new CustomEvent('join-session', {
      detail: { sessionId, campaignId: this.campaignId },
      bubbles: true,
      composed: true,
    }));
  }

  private handleCreateSession() {
    this.isCreateModalOpen = true;
  }

  render() {
    return html`
      <div class="sessions-card">
        <div class="header-row">
          <div class="title-group">
            <h3>Campaign Sessions</h3>
            <p>Active virtual tabletops and scheduled adventure gatherings</p>
          </div>
          ${this.isDm ? html`
            <button class="btn-create" type="button" @click=${this.handleCreateSession}>
              + New Session
            </button>
          ` : ''}
        </div>

        ${this.sessions.length > 0 ? html`
          <div class="sessions-list">
            ${this.sessions.map((s) => html`
              <div class="session-item" data-session-id=${s.id}>
                <div class="session-info">
                  <div class="session-title-row">
                    <span class="session-title">${s.title}</span>
                    <span class="badge-status badge-${s.status}">
                      ${s.status === 'active' ? '● Live VTT' : s.status === 'lobby' ? '⧖ Pre-Game Lobby' : s.status === 'upcoming' ? '📅 Upcoming' : s.status}
                    </span>
                  </div>
                  <div class="session-meta">
                    Session ID: ${s.id} ${s.participantsCount ? `• ${s.participantsCount} Assembled` : ''}
                    ${s.scheduledAt || s.scheduled_at ? html`• <span class="session-schedule">Scheduled: ${s.scheduledAt || s.scheduled_at}</span>` : ''}
                  </div>
                  ${s.description ? html`<div class="session-description">${s.description}</div>` : ''}
                </div>
                <div class="action-group">
                  <button class="btn-action" type="button" @click=${() => this.handleEnterLobby(s.id)}>
                    ${s.status === 'upcoming' ? 'Open Staging' : 'Enter Lobby'}
                  </button>
                  <button class="btn-action primary" type="button" @click=${() => this.handleJoinSession(s.id)}>
                    Join Tabletop
                  </button>
                </div>
              </div>
            `)}
          </div>
        ` : html`
          <div class="empty-state">
            <p>No active or scheduled sessions for this campaign yet.</p>
            ${this.isDm ? html`
              <button class="btn-create" type="button" @click=${this.handleCreateSession}>
                Create Staging Lobby
              </button>
            ` : ''}
          </div>
        `}
      </div>

      <runefoble-session-modal
        .open=${this.isCreateModalOpen}
        campaign-id=${this.campaignId}
        @modal-closed=${() => { this.isCreateModalOpen = false; }}
        @create-session=${() => { this.isCreateModalOpen = false; }}
      ></runefoble-session-modal>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-session-list': RunefobleSessionList;
  }
}
