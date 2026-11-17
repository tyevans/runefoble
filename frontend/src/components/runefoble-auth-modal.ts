/**
 * Runefoble Zitadel Sign-In Gate Component
 * ADR-0004, ADR-0012, ADR-0013, ADR-0015 (d), TASK-0207, TASK-0524
 *
 * The modal holds no credential field. Sign-in and hosted sign-up both send the user to Zitadel.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { authService } from '../auth/auth-service.ts';

@customElement('runefoble-auth-modal')
export class RunefobleAuthModal extends LitElement {
  @property({ type: Boolean, reflect: true }) open = false;
  @property({ type: String }) errorMessage = '';
  /** True while the browser leaves for Zitadel. Set by the parent or by this component. */
  @property({ type: Boolean }) busy = false;

  @state() private localError = '';

  static styles = css`
    :host { display: contents; }
    .backdrop {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65);
      display: flex; align-items: center; justify-content: center;
      z-index: var(--rf-z-modal, 1000); padding: 16px;
    }
    .modal-card {
      background: var(--rf-bg-surface, #fff); color: var(--rf-text-primary, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      width: 100%; max-width: 440px; padding: 24px; display: flex; flex-direction: column; gap: 16px;
    }
    .header { display: flex; justify-content: space-between; align-items: center; }
    .title { font-size: 1.4rem; font-weight: 900; margin: 0; letter-spacing: -0.5px; }
    .close-btn {
      background: none; border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      cursor: pointer; font-size: 1.1rem; line-height: 1; padding: 4px 8px; font-weight: 800;
    }
    .intro { margin: 0; font-size: 0.95rem; line-height: 1.4; }
    .actions { display: flex; flex-direction: column; gap: 12px; }
    .error-banner {
      background: var(--rf-accent-primary, #e63946); color: #fff;
      padding: 8px 12px; font-size: 0.85rem; font-weight: 700;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    }
    .submit-btn {
      background: var(--rf-accent-primary, #e63946); color: #fff;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212); padding: 10px;
      font-weight: 800; font-size: 0.95rem; cursor: pointer; text-transform: uppercase;
    }
    .secondary-btn {
      background: var(--rf-bg-inset, #f1f3f5); color: var(--rf-text-primary, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      padding: 10px; font-weight: 800; font-size: 0.95rem; cursor: pointer; text-transform: uppercase;
    }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
  `;

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('errorMessage')) this.localError = this.errorMessage;
  }

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('keydown', this.handleKeydown);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this.handleKeydown);
  }

  private handleKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && this.open) this.handleClose();
  };

  private handleClose() {
    this.open = false;
    this.localError = '';
    this.dispatchEvent(new CustomEvent('auth-modal-closed', { bubbles: true, composed: true }));
  }

  private async startSignIn(signUp: boolean) {
    this.busy = true;
    this.localError = '';
    try {
      await authService.startSignIn({ signUp });
    } catch (err) {
      this.busy = false;
      this.localError = err instanceof Error ? err.message : 'Sign-in could not start.';
    }
  }

  render() {
    if (!this.open) return html``;
    return html`
      <div class="backdrop" @click=${(e: Event) => e.target === e.currentTarget && this.handleClose()}>
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
          <div class="header">
            <h2 id="auth-modal-title" class="title">Zitadel Identity</h2>
            <button class="close-btn" aria-label="Close modal" @click=${this.handleClose}>×</button>
          </div>
          <p class="intro">Sign in with your Zitadel account. Enter your password on the Zitadel page only.</p>
          ${this.localError ? html`<div class="error-banner" role="alert">${this.localError}</div>` : ''}
          <div class="actions">
            <button type="button" class="submit-btn" ?disabled=${this.busy} @click=${() => this.startSignIn(false)}>
              ${this.busy ? 'Redirecting to Zitadel...' : 'Sign In with Zitadel'}
            </button>
            <button type="button" class="secondary-btn" ?disabled=${this.busy} @click=${() => this.startSignIn(true)}>
              Create Account
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-auth-modal': RunefobleAuthModal;
  }
}
