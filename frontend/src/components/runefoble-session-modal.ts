/**
 * Runefoble Session Scheduling and Staging Lobby Creation Modal
 * TASK-0249: Session Scheduling and Staging Lobby Creation Modal
 * Governed by ADR-0001, ADR-0004, ADR-0007, ADR-0012.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

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

  static styles = css`
    :host {
      display: contents;
    }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: var(--rf-z-modal, 1000);
      padding: 16px;
    }
    .modal-card {
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-primary, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      width: 100%;
      max-width: 520px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding-bottom: 12px;
    }
    .modal-title {
      font-size: 1.25rem;
      font-weight: 800;
      margin: 0;
      color: var(--rf-text-primary, #121212);
      letter-spacing: -0.3px;
    }
    .btn-close {
      background: none;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      cursor: pointer;
      font-size: 1.2rem;
      font-weight: 800;
      padding: 2px 8px;
      line-height: 1;
      color: var(--rf-text-primary, #121212);
      transition: transform 0.1s ease;
    }
    .btn-close:hover {
      transform: translate(-1px, -1px);
    }
    form {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    label {
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--rf-text-primary, #121212);
      letter-spacing: 0.5px;
    }
    .required {
      color: var(--rf-accent-primary, #e63946);
    }
    input,
    select,
    textarea {
      padding: 8px 10px;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      background: var(--rf-bg-canvas, #ffffff);
      color: var(--rf-text-primary, #121212);
      font-size: 0.95rem;
      font-family: inherit;
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }
    input:focus,
    select:focus,
    textarea:focus {
      outline: none;
      border-color: var(--rf-accent-secondary, #1d3557);
    }
    textarea {
      resize: vertical;
      min-height: 70px;
    }
    .error-banner {
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
      padding: 8px 12px;
      font-size: 0.85rem;
      font-weight: 700;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    }
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 8px;
    }
    .btn-cancel {
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-primary, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-weight: 800;
      font-size: 0.85rem;
      padding: 8px 16px;
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .btn-cancel:hover {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }
    .btn-submit {
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-weight: 800;
      font-size: 0.85rem;
      padding: 8px 18px;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .btn-submit:hover:not(:disabled) {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }
    .btn-submit:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `;

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('errorMessage')) {
      this.localError = this.errorMessage;
    }
    if (changed.has('initialStatus')) {
      this.status = this.initialStatus;
    }
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
    if (e.key === 'Escape' && this.open) {
      this.handleClose();
    }
  };

  private handleClose() {
    this.open = false;
    this.localError = '';
    this.dispatchEvent(new CustomEvent('modal-closed', { bubbles: true, composed: true }));
  }

  private handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      this.handleClose();
    }
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
      scheduledAt: this.scheduledAt ? this.scheduledAt : undefined,
      scheduled_at: this.scheduledAt ? this.scheduledAt : undefined,
      description: this.description.trim(),
      status: this.status,
    };

    this.dispatchEvent(
      new CustomEvent('create-session', {
        detail,
        bubbles: true,
        composed: true,
      })
    );

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

  render() {
    if (!this.open) return html``;

    const activeError = this.localError || this.errorMessage;

    return html`
      <div
        class="modal-backdrop"
        @click=${this.handleBackdropClick}
      >
        <div
          class="modal-card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="session-modal-title"
        >
          <div class="modal-header">
            <h2 id="session-modal-title" class="modal-title">Create / Schedule Session</h2>
            <button
              class="btn-close"
              aria-label="Close modal"
              type="button"
              @click=${this.handleClose}
            >
              ×
            </button>
          </div>

          <form @submit=${this.handleSubmit}>
            ${activeError
              ? html`<div class="error-banner" role="alert">${activeError}</div>`
              : ''}

            <div class="form-group">
              <label for="session-title">
                Session Title <span class="required">*</span>
              </label>
              <input
                id="session-title"
                name="title"
                type="text"
                placeholder="e.g. Chapter 4: The Sunken Vault"
                .value=${this.sessionTitle}
                @input=${(e: Event) => {
                  this.sessionTitle = (e.target as HTMLInputElement).value;
                  if (this.localError) this.localError = '';
                }}
                required
              />
            </div>

            <div class="form-group">
              <label for="session-status">Initial Status</label>
              <select
                id="session-status"
                name="status"
                .value=${this.status}
                @change=${(e: Event) => {
                  this.status = (e.target as HTMLSelectElement).value as 'lobby' | 'upcoming';
                }}
              >
                <option value="lobby">Pre-Game Staging Lobby (Immediate)</option>
                <option value="upcoming">Upcoming Session (Scheduled)</option>
              </select>
            </div>

            <div class="form-group">
              <label for="scheduled-at">Scheduled Date & Time</label>
              <input
                id="scheduled-at"
                name="scheduledAt"
                type="datetime-local"
                .value=${this.scheduledAt}
                @input=${(e: Event) => {
                  this.scheduledAt = (e.target as HTMLInputElement).value;
                }}
              />
            </div>

            <div class="form-group">
              <label for="session-description">Description & DM Notes</label>
              <textarea
                id="session-description"
                name="description"
                rows="3"
                placeholder="Scenario briefing, objective recap, or staging preparation..."
                .value=${this.description}
                @input=${(e: Event) => {
                  this.description = (e.target as HTMLTextAreaElement).value;
                }}
              ></textarea>
            </div>

            <div class="modal-actions">
              <button
                type="button"
                class="btn-cancel"
                @click=${this.handleClose}
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn-submit"
                ?disabled=${this.isSubmitting}
              >
                Create Session
              </button>
            </div>
          </form>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-session-modal': RunefobleSessionModal;
  }
}
