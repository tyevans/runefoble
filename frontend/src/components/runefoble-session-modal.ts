/**
 * Runefoble Session Scheduling and Staging Lobby Creation Modal (TASK-0249, TASK-0270).
 * Governed by ADR-0001, ADR-0004, ADR-0007, ADR-0012.
 */
import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { sessionModalStyles } from '../styles/session-modal.styles.ts';

export interface CreateSessionDetail {
  campaignId?: string;
  title: string;
  scheduledAt?: string;
  scheduled_at?: string;
  description?: string;
  status: 'lobby' | 'upcoming';
}

@customElement('runefoble-session-modal')
export class RunefobleSessionModal extends LitElement {
  @property({ type: Boolean, reflect: true }) open = false;
  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: String }) errorMessage = '';
  @property({ type: String }) initialStatus: 'lobby' | 'upcoming' = 'lobby';
  @property({ type: String, attribute: 'session-title' }) sessionTitle = '';

  @state() private scheduledAt = '';
  @state() private description = '';
  @state() private status: 'lobby' | 'upcoming' = 'lobby';
  @state() private localError = '';
  @state() private isSubmitting = false;

  static styles = sessionModalStyles;

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('errorMessage')) this.localError = this.errorMessage;
    if (changed.has('initialStatus')) this.status = this.initialStatus;
  }

  connectedCallback() {
    super.connectedCallback();
    this.status = this.initialStatus;
    window.addEventListener('keydown', this.handleKeyDown);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this.handleKeyDown);
  }

  private handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && this.open) this.handleClose();
  };

  private handleClose() {
    this.open = false;
    this.localError = '';
    this.dispatchEvent(new CustomEvent('modal-closed', { bubbles: true, composed: true }));
  }

  private handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) this.handleClose();
  }

  private validate(): boolean {
    const trimmed = this.sessionTitle.trim();
    if (!trimmed) {
      this.localError = 'Session title is required';
      return false;
    }
    if (trimmed.length > 120) {
      this.localError = 'Session title must be 120 characters or less';
      return false;
    }
    this.localError = '';
    return true;
  }

  private handleSubmit(e: Event) {
    e.preventDefault();
    if (!this.validate()) return;
    const detail: CreateSessionDetail = {
      campaignId: this.campaignId || undefined,
      title: this.sessionTitle.trim(),
      scheduledAt: this.scheduledAt || undefined,
      scheduled_at: this.scheduledAt || undefined,
      description: this.description.trim(),
      status: this.status,
    };
    this.dispatchEvent(new CustomEvent('create-session', { detail, bubbles: true, composed: true }));
    this.resetForm();
    this.open = false;
  }

  public resetForm() {
    this.sessionTitle = '';
    this.scheduledAt = '';
    this.description = '';
    this.status = this.initialStatus || 'lobby';
    this.localError = '';
    this.isSubmitting = false;
  }

  private renderHeader() {
    return html`<div class="modal-header">
      <h2 id="session-modal-title" class="modal-title">Create / Schedule Session</h2>
      <button class="btn-close" aria-label="Close modal" type="button" @click=${this.handleClose}>×</button>
    </div>`;
  }

  private renderTitleField() {
    return html`<div class="form-group">
      <label for="session-title">Session Title <span class="required">*</span></label>
      <input id="session-title" name="title" type="text" placeholder="e.g. Chapter 4: The Sunken Vault"
        .value=${this.sessionTitle} required
        @input=${(e: Event) => { this.sessionTitle = (e.target as HTMLInputElement).value; if (this.localError) this.localError = ''; }} />
    </div>`;
  }

  private renderStatusField() {
    return html`<div class="form-group">
      <label for="session-status">Initial Status</label>
      <select id="session-status" name="status" .value=${this.status}
        @change=${(e: Event) => { this.status = (e.target as HTMLSelectElement).value as 'lobby' | 'upcoming'; }}>
        <option value="lobby">Pre-Game Staging Lobby (Immediate)</option>
        <option value="upcoming">Upcoming Session (Scheduled)</option>
      </select>
    </div>`;
  }

  private renderScheduleField() {
    return html`<div class="form-group">
      <label for="scheduled-at">Scheduled Date & Time</label>
      <input id="scheduled-at" name="scheduledAt" type="datetime-local" .value=${this.scheduledAt}
        @input=${(e: Event) => { this.scheduledAt = (e.target as HTMLInputElement).value; }} />
    </div>`;
  }

  private renderDescriptionField() {
    return html`<div class="form-group">
      <label for="session-description">Description & DM Notes</label>
      <textarea id="session-description" name="description" rows="3"
        placeholder="Scenario briefing, objective recap, or staging preparation..."
        .value=${this.description}
        @input=${(e: Event) => { this.description = (e.target as HTMLTextAreaElement).value; }}></textarea>
    </div>`;
  }

  private renderActions() {
    return html`<div class="modal-actions">
      <button type="button" class="btn-cancel" @click=${this.handleClose}>Cancel</button>
      <button type="submit" class="btn-submit" ?disabled=${this.isSubmitting}>Create Session</button>
    </div>`;
  }

  render() {
    if (!this.open) return html``;
    const activeError = this.localError || this.errorMessage;
    return html`
      <div class="modal-backdrop" @click=${this.handleBackdropClick}>
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="session-modal-title">
          ${this.renderHeader()}
          <form @submit=${this.handleSubmit}>
            ${activeError ? html`<div class="error-banner" role="alert">${activeError}</div>` : ''}
            ${this.renderTitleField()}${this.renderStatusField()}
            ${this.renderScheduleField()}${this.renderDescriptionField()}
            ${this.renderActions()}
          </form>
        </div>
      </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-session-modal': RunefobleSessionModal;
  }
}
