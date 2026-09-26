import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { dmWhisperBarStyles } from './runefoble-dm-whisper-bar.styles.ts';

export interface WhisperItem {
  whisper_id: string;
  whisper_type: 'atmospheric_hint' | 'monster_tactics' | 'passive_perception' | 'narrative_secret' | string;
  content: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export interface PendingActionItem {
  action_id: string;
  actor_name: string;
  action_type: string;
  description: string;
  target?: string | null;
  parameters?: Record<string, unknown>;
  status?: string;
  pause_window_ms?: number;
}

@customElement('runefoble-dm-whisper-bar')
export class RunefobleDmWhisperBar extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) campaignId = '';
  @property({ type: Number }) pauseWindowMs = 2000;

  @property({ type: Array }) whispers: WhisperItem[] = [
    {
      whisper_id: 'whisp-1',
      whisper_type: 'atmospheric_hint',
      content: 'Damp cavern walls seep with glowing mineral salts that flicker when torches approach.',
    },
    {
      whisper_id: 'whisp-2',
      whisper_type: 'monster_tactics',
      content: 'Goblin skirmishers prepare to disengage and flank squishy spellcasters.',
    },
    {
      whisper_id: 'whisp-3',
      whisper_type: 'passive_perception',
      content: 'Passive Perception >= 14 spots the tripwire trap 10ft ahead.',
    },
  ];

  @property({ type: Object }) pendingAction: PendingActionItem | null = null;

  @state() private remainingMs = 2000;
  @state() private isEditing = false;
  @state() private editDescription = '';
  @state() private editTarget = '';
  @state() private activeTab = 'all';

  private timerInterval: number | null = null;

  static styles = dmWhisperBarStyles;

  connectedCallback() {
    super.connectedCallback();
    if (this.pendingAction) {
      this.startCountdown();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.stopCountdown();
  }

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has('pendingAction')) {
      if (this.pendingAction && this.pendingAction.status !== 'vetoed' && this.pendingAction.status !== 'approved') {
        this.editDescription = this.pendingAction.description;
        this.editTarget = this.pendingAction.target || '';
        this.startCountdown();
      } else {
        this.stopCountdown();
      }
    }
  }

  private startCountdown() {
    this.stopCountdown();
    const duration = this.pendingAction?.pause_window_ms || this.pauseWindowMs;
    this.remainingMs = duration;
    const intervalStep = 100;

    this.timerInterval = window.setInterval(() => {
      this.remainingMs = Math.max(0, this.remainingMs - intervalStep);
      if (this.remainingMs <= 0) {
        this.stopCountdown();
      }
    }, intervalStep);
  }

  private stopCountdown() {
    if (this.timerInterval !== null) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private handleApprove() {
    if (!this.pendingAction) return;
    this.stopCountdown();
    this.dispatchEvent(
      new CustomEvent('action-approved', {
        detail: { actionId: this.pendingAction.action_id },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleVeto() {
    if (!this.pendingAction) return;
    this.stopCountdown();
    this.dispatchEvent(
      new CustomEvent('action-vetoed', {
        detail: { actionId: this.pendingAction.action_id, reason: 'DM one-click veto' },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleStartEdit() {
    if (!this.pendingAction) return;
    this.isEditing = true;
    this.editDescription = this.pendingAction.description;
    this.editTarget = this.pendingAction.target || '';
  }

  private handleCancelEdit() {
    this.isEditing = false;
  }

  private handleSaveEdit(autoApprove = true) {
    if (!this.pendingAction) return;
    this.isEditing = false;
    this.stopCountdown();
    this.dispatchEvent(
      new CustomEvent('action-modified', {
        detail: {
          actionId: this.pendingAction.action_id,
          description: this.editDescription,
          target: this.editTarget,
          autoApprove,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const totalDuration = this.pendingAction?.pause_window_ms || this.pauseWindowMs;
    const progressPercent = totalDuration > 0 ? (this.remainingMs / totalDuration) * 100 : 0;

    const filteredWhispers =
      this.activeTab === 'all'
        ? this.whispers
        : this.whispers.filter((w) => w.whisper_type === this.activeTab);

    return html`
      <div class="header">
        <div class="title-group">
          <h3>DM Co-Pilot Whisper Bar</h3>
          <span class="badge badge-dm">🔒 DM Secure Channel</span>
        </div>
        ${this.pendingAction
          ? html`<span class="badge badge-pending">⚡ Action Intercepted</span>`
          : ''}
      </div>

      ${this.pendingAction
        ? html`
            <div class="interceptor-box">
              <div class="interceptor-header">
                <div class="interceptor-title">
                  ⚠️ AI Action Intercepted (${Math.ceil(this.remainingMs / 1000)}s pause window)
                </div>
                <span class="badge badge-whisper-type">${this.pendingAction.action_type}</span>
              </div>

              <div class="countdown-bar">
                <div class="countdown-fill" style="width: ${progressPercent}%;"></div>
              </div>

              <div class="action-details">
                <span class="action-actor">${this.pendingAction.actor_name}:</span>
                ${this.pendingAction.description}
                ${this.pendingAction.target
                  ? html` &rarr; <strong>Target: ${this.pendingAction.target}</strong>`
                  : ''}
              </div>

              ${this.isEditing
                ? html`
                    <div class="edit-form">
                      <div class="form-row">
                        <label>Description</label>
                        <input
                          type="text"
                          .value=${this.editDescription}
                          @input=${(e: Event) =>
                            (this.editDescription = (e.target as HTMLInputElement).value)}
                        />
                      </div>
                      <div class="form-row">
                        <label>Target</label>
                        <input
                          type="text"
                          .value=${this.editTarget}
                          @input=${(e: Event) =>
                            (this.editTarget = (e.target as HTMLInputElement).value)}
                        />
                      </div>
                      <div class="action-controls" style="margin-top: 6px;">
                        <button class="rf-btn btn-approve" @click=${() => this.handleSaveEdit(true)}>
                          Save & Approve
                        </button>
                        <button class="rf-btn" @click=${this.handleCancelEdit}>Cancel</button>
                      </div>
                    </div>
                  `
                : html`
                    <div class="action-controls">
                      <button class="rf-btn btn-approve" @click=${this.handleApprove}>Approve</button>
                      <button class="rf-btn btn-veto" @click=${this.handleVeto}>Veto</button>
                      <button class="rf-btn btn-edit" @click=${this.handleStartEdit}>
                        Edit Intent
                      </button>
                    </div>
                  `}
            </div>
          `
        : ''}

      <div class="whisper-section">
        <div class="section-title">
          <span>Private Narrative Whispers</span>
          <span style="font-size: 0.75rem; color: #6b7280;">${filteredWhispers.length} Suggestions</span>
        </div>

        <div class="filter-tabs">
          <button
            class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}"
            @click=${() => (this.activeTab = 'all')}
          >
            All
          </button>
          <button
            class="tab-btn ${this.activeTab === 'atmospheric_hint' ? 'active' : ''}"
            @click=${() => (this.activeTab = 'atmospheric_hint')}
          >
            Atmosphere
          </button>
          <button
            class="tab-btn ${this.activeTab === 'monster_tactics' ? 'active' : ''}"
            @click=${() => (this.activeTab = 'monster_tactics')}
          >
            Tactics
          </button>
          <button
            class="tab-btn ${this.activeTab === 'passive_perception' ? 'active' : ''}"
            @click=${() => (this.activeTab = 'passive_perception')}
          >
            Perception
          </button>
        </div>

        <div class="whisper-list">
          ${filteredWhispers.length === 0
            ? html`<div class="empty-state">No whispers in this category.</div>`
            : filteredWhispers.map(
                (w) => html`
                  <div class="whisper-card">
                    <div class="whisper-header">
                      <span class="badge badge-whisper-type">${w.whisper_type.replace('_', ' ')}</span>
                    </div>
                    <div class="whisper-content">${w.content}</div>
                  </div>
                `
              )}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-dm-whisper-bar': RunefobleDmWhisperBar;
  }
}
