/**
 * DM co-pilot whisper bar (TASK-0093, TASK-0838, TASK-0949).
 *
 * The bar starts with no whisper. When it has a session and a campaign id, it reads the DM
 * whispers and the open action through the gateway. The DM asks for a whisper with
 * "Ask for a whisper". The text comes only from the language model. When no model is configured,
 * the bar says so and shows no invented text (ADR-0015, ADR-0022).
 *
 * Veto: the bar sends `action-vetoed`. The host posts the veto route, then calls
 * `markActionVetoed` or `showActionError`. Approve and Edit send `action-approved` and
 * `action-modified`.
 */

import { AuthConsumerController, actionFailureMessage } from '@runefoble/ui-core';
import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { dmWhisperBarStyles } from './runefoble-dm-whisper-bar.styles.ts';
import { whisperAction } from './whisper-actions.ts';
import { NO_NARRATION_ENGINE, fetchPendingActions, fetchWhispers, generateWhispers, openAction } from './whisper-bar-api.ts';
import { renderInterceptor } from './whisper-bar-interceptor.template.ts';
import type { ActionVetoedDetail, PendingActionItem, WhisperItem } from './whisper-bar-types.ts';

export const NO_MODEL_TEXT = 'No language model is configured for whispers.';
const NARRATION_TAB = 'narration';

@customElement('runefoble-dm-whisper-bar')
export class RunefobleDmWhisperBar extends LitElement {
  private readonly auth = new AuthConsumerController(this);

  @property({ type: String }) sessionId = '';
  @property({ type: String }) campaignId = '';
  /** Gateway origin. Empty means the page origin. */
  @property({ type: String }) apiBaseUrl = '';
  @property({ type: Number }) pauseWindowMs = 2000;
  @property({ type: Array }) whispers: WhisperItem[] = [];
  @property({ type: Object }) pendingAction: PendingActionItem | null = null;
  /** Engine of the narration port, from the whisper list. `none` shows the no-model state. */
  @property({ type: String }) narrationEngine = '';

  @state() private remainingMs = 2000;
  @state() private isEditing = false;
  @state() private editDescription = '';
  @state() private editTarget = '';
  @state() private activeTab = 'all';
  @state() private loadError = '';
  @state() private generateError = '';
  @state() private actionError = '';
  @state() private generating = false;

  private timerInterval: number | null = null;
  private loadedScope = '';

  static styles = dmWhisperBarStyles;

  connectedCallback() {
    super.connectedCallback();
    globalThis.addEventListener('runefoble:dm-whisper', this.onSessionDmWhisper);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    globalThis.removeEventListener('runefoble:dm-whisper', this.onSessionDmWhisper);
    this.stopCountdown();
  }

  /** The host's veto call succeeded. The action shows as vetoed and its countdown stops. */
  public markActionVetoed(actionId: string): void {
    if (this.pendingAction?.action_id !== actionId) return;
    this.actionError = '';
    this.pendingAction = { ...this.pendingAction, status: 'vetoed' };
  }

  /** The host's call for the open action failed. The bar shows the reason. */
  public showActionError(message: string): void {
    this.actionError = message;
  }

  /** Session `dm_whisper` message (window event `runefoble:dm-whisper`): add the whisper to the bar. */
  private readonly onSessionDmWhisper = (e: Event): void => {
    const msg = (e as CustomEvent<Record<string, any>>).detail;
    const whisper: WhisperItem | undefined = msg.whisper;
    if (whisper && !this.whispers.some((w) => w.whisper_id === whisper.whisper_id)) {
      this.whispers = [...this.whispers, whisper];
    }
  };

  updated(changed: Map<string, unknown>) {
    if (changed.has('sessionId') || changed.has('campaignId') || changed.has('apiBaseUrl')) {
      void this.loadSession();
    }
    if (changed.has('pendingAction')) this.onPendingActionChanged();
  }

  private scope() {
    return { sessionId: this.sessionId, campaignId: this.campaignId };
  }

  private opts() {
    return { apiBase: this.apiBaseUrl, auth: this.auth };
  }

  /** Reads the whispers and the open action once for each session. */
  private async loadSession(): Promise<void> {
    if (!this.sessionId || !this.campaignId) return;
    const key = `${this.apiBaseUrl}|${this.sessionId}|${this.campaignId}`;
    if (key === this.loadedScope) return;
    this.loadedScope = key;
    try {
      const listed = await fetchWhispers(this.scope(), this.opts());
      this.whispers = listed.whispers;
      this.narrationEngine = listed.narration_engine;
      this.pendingAction = openAction(await fetchPendingActions(this.scope(), this.opts()));
      this.loadError = '';
    } catch (err) {
      this.loadError = actionFailureMessage(err, 'whisper request');
    }
  }

  private async handleGenerate(): Promise<void> {
    this.generating = true;
    try {
      const created = await generateWhispers(this.scope(), this.opts());
      const known = new Set(this.whispers.map((w) => w.whisper_id));
      this.whispers = [...this.whispers, ...created.filter((w) => !known.has(w.whisper_id))];
      this.generateError = '';
    } catch (err) {
      this.generateError = actionFailureMessage(err, 'whisper request');
    } finally {
      this.generating = false;
    }
  }

  private onPendingActionChanged() {
    const action = this.pendingAction;
    if (action && (action.status === undefined || action.status === 'pending' || action.status === 'modified')) {
      this.editDescription = action.description;
      this.editTarget = action.target || '';
      this.startCountdown();
    } else {
      this.stopCountdown();
    }
  }

  private startCountdown() {
    this.stopCountdown();
    const total = this.pendingAction?.pause_window_ms || this.pauseWindowMs;
    const expiresAt = this.pendingAction?.expires_at;
    this.remainingMs = expiresAt ? Math.min(total, Math.max(0, expiresAt * 1000 - Date.now())) : total;
    const intervalStep = 100;
    this.timerInterval = window.setInterval(() => {
      this.remainingMs = Math.max(0, this.remainingMs - intervalStep);
      if (this.remainingMs <= 0) this.stopCountdown();
    }, intervalStep);
  }

  private stopCountdown() {
    if (this.timerInterval !== null) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private emit(name: string, detail: object) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  private handleApprove() {
    if (!this.pendingAction) return;
    this.stopCountdown();
    this.emit('action-approved', { actionId: this.pendingAction.action_id });
  }

  private handleVeto() {
    if (!this.pendingAction) return;
    const detail: ActionVetoedDetail = {
      actionId: this.pendingAction.action_id,
      reason: 'DM one-click veto',
      sessionId: this.sessionId,
      campaignId: this.campaignId,
    };
    this.emit('action-vetoed', detail);
  }

  private handleSaveEdit() {
    if (!this.pendingAction) return;
    this.isEditing = false;
    this.stopCountdown();
    this.emit('action-modified', {
      actionId: this.pendingAction.action_id,
      description: this.editDescription,
      target: this.editTarget,
      autoApprove: true,
    });
  }

  /** Ask the host to send an audience narration to the table (TASK-0838). The host posts the DM route. */
  private handleSendNarration(w: WhisperItem) {
    this.emit('narration-send', { whisperId: w.whisper_id, text: w.content, sessionId: this.sessionId, campaignId: this.campaignId });
  }

  private renderWhisper(w: WhisperItem) {
    const action = whisperAction(w);
    return html`
      <div class="whisper-card" data-whisper-type=${w.whisper_type}>
        <div class="whisper-header">
          <span class="badge badge-whisper-type">${w.whisper_type.replaceAll('_', ' ')}</span>
        </div>
        ${action === 'notice'
          ? html`<div class="whisper-notice" role="status">${w.content}</div>`
          : html`<div class="whisper-content">${w.content}</div>`}
        ${action === 'send'
          ? html`<div class="whisper-actions">
              <button class="rf-btn btn-approve" @click=${() => this.handleSendNarration(w)}>Send to table</button>
            </div>`
          : action === 'sent'
            ? html`<div class="whisper-actions"><span class="sent-badge">Sent to table</span></div>`
            : ''}
      </div>
    `;
  }

  private renderModelState() {
    if (this.narrationEngine === NO_NARRATION_ENGINE) {
      return html`<div class="bar-status no-model" role="status">${NO_MODEL_TEXT}</div>`;
    }
    if (!this.sessionId || !this.campaignId) return '';
    return html`
      <div class="whisper-actions">
        <button class="rf-btn btn-generate" ?disabled=${this.generating} @click=${() => this.handleGenerate()}>
          ${this.generating ? 'Asking the model...' : 'Ask for a whisper'}
        </button>
      </div>
      ${this.generateError ? html`<div class="bar-error" role="alert">${this.generateError}</div>` : ''}
    `;
  }

  private renderTabs() {
    const tab = (id: string, label: string) => html`
      <button class="tab-btn ${this.activeTab === id ? 'active' : ''}" @click=${() => (this.activeTab = id)}>${label}</button>
    `;
    return html`<div class="filter-tabs">${tab('all', 'All')}${tab(NARRATION_TAB, 'Narration')}</div>`;
  }

  render() {
    const shown = this.activeTab === 'all' ? this.whispers : this.whispers.filter((w) => w.whisper_type === this.activeTab);
    const open = this.pendingAction && this.pendingAction.status !== 'vetoed';
    return html`
      <div class="header">
        <div class="title-group">
          <h3>DM Co-Pilot Whisper Bar</h3>
          <span class="badge badge-dm">🔒 DM Secure Channel</span>
        </div>
        ${open ? html`<span class="badge badge-pending">⚡ Action Intercepted</span>` : ''}
      </div>

      ${this.loadError ? html`<div class="bar-error" role="alert">${this.loadError}</div>` : ''}

      ${this.pendingAction
        ? renderInterceptor(
            {
              action: this.pendingAction,
              remainingMs: this.remainingMs,
              totalMs: this.pendingAction.pause_window_ms || this.pauseWindowMs,
              isEditing: this.isEditing,
              editDescription: this.editDescription,
              editTarget: this.editTarget,
              actionError: this.actionError,
            },
            {
              approve: () => this.handleApprove(),
              veto: () => this.handleVeto(),
              startEdit: () => { this.isEditing = true; },
              cancelEdit: () => { this.isEditing = false; },
              saveEdit: () => this.handleSaveEdit(),
              editDescription: (v) => { this.editDescription = v; },
              editTarget: (v) => { this.editTarget = v; },
            },
          )
        : ''}

      <div class="whisper-section">
        <div class="section-title">
          <span>Private Narrative Whispers</span>
          <span style="font-size: 0.75rem; color: var(--rf-text-muted);">${shown.length} Suggestions</span>
        </div>
        ${this.renderModelState()}
        ${this.renderTabs()}
        <div class="whisper-list">
          ${shown.length === 0
            ? html`<div class="empty-state">No whispers yet.</div>`
            : shown.map((w) => this.renderWhisper(w))}
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
