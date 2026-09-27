/**
 * Runefoble Zitadel Authentication Modal Component
 * ADR-0004, ADR-0012, ADR-0013, TASK-0207
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { router } from '../router/router.ts';

@customElement('runefoble-auth-modal')
export class RunefobleAuthModal extends LitElement {
  @property({ type: Boolean, reflect: true }) open = false;
  @property({ type: String }) initialTab: 'login' | 'register' = 'login';
  @property({ type: String }) errorMessage = '';

  @state() private activeTab: 'login' | 'register' = 'login';
  @state() private username = '';
  @state() private email = '';
  @state() private password = '';
  @state() private confirmPassword = '';
  @state() private localError = '';
  @state() private isLoading = false;

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
    .tabs { display: flex; gap: 8px; border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212); padding-bottom: 8px; }
    .tab-btn {
      background: var(--rf-bg-inset, #f1f3f5); border: var(--rf-border-width, 2px) solid transparent;
      padding: 6px 14px; font-weight: 700; cursor: pointer; color: var(--rf-text-muted, #4b5563);
    }
    .tab-btn.active {
      background: var(--rf-accent-secondary, #1d3557); color: #fff;
      border-color: var(--rf-border-color, #121212); box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }
    form { display: flex; flex-direction: column; gap: 12px; }
    .form-group { display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; }
    input {
      padding: 8px 10px; border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      background: var(--rf-bg-surface, #fff); color: var(--rf-text-primary, #121212);
      font-size: 0.95rem; font-family: inherit;
    }
    input:focus { outline: none; border-color: var(--rf-accent-secondary, #1d3557); }
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
    .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  `;

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has('initialTab')) this.activeTab = this.initialTab;
    if (changed.has('errorMessage')) this.localError = this.errorMessage;
  }

  connectedCallback() {
    super.connectedCallback();
    this.activeTab = this.initialTab;
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

  private validate(): boolean {
    if (!this.username.trim()) { this.localError = 'Username is required'; return false; }
    if (!this.password) { this.localError = 'Password is required'; return false; }
    if (this.activeTab === 'register') {
      if (!this.email || !/\S+@\S+\.\S+/.test(this.email)) {
        this.localError = 'A valid email address is required'; return false;
      }
      if (this.password.length < 8) {
        this.localError = 'Password must be at least 8 characters'; return false;
      }
      if (this.password !== this.confirmPassword) {
        this.localError = 'Passwords do not match'; return false;
      }
    }
    this.localError = '';
    return true;
  }

  private async handleSubmit(e: Event) {
    e.preventDefault();
    if (!this.validate()) return;
    this.isLoading = true;
    try {
      let user: UserClaims;
      if (this.activeTab === 'login') {
        user = await authService.login(this.username, this.password);
      } else {
        user = await authService.register(this.username, this.email, this.password);
      }
      this.dispatchEvent(new CustomEvent('auth-success', { detail: { user }, bubbles: true, composed: true }));
      this.open = false;
      router.navigate('#/campaigns');
    } catch (err) {
      this.localError = err instanceof Error ? err.message : 'Authentication failed';
    } finally {
      this.isLoading = false;
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
          <div class="tabs" role="tablist">
            <button class="tab-btn ${this.activeTab === 'login' ? 'active' : ''}" role="tab"
              aria-selected="${this.activeTab === 'login'}" @click=${() => { this.activeTab = 'login'; this.localError = ''; }}>
              Sign In
            </button>
            <button class="tab-btn ${this.activeTab === 'register' ? 'active' : ''}" role="tab"
              aria-selected="${this.activeTab === 'register'}" @click=${() => { this.activeTab = 'register'; this.localError = ''; }}>
              Create Account
            </button>
          </div>
          ${this.localError ? html`<div class="error-banner" role="alert">${this.localError}</div>` : ''}
          <form @submit=${this.handleSubmit}>
            <div class="form-group">
              <label for="rf-auth-username">Username</label>
              <input id="rf-auth-username" type="text" .value=${this.username} autocomplete="username"
                @input=${(e: Event) => { this.username = (e.target as HTMLInputElement).value; }} required />
            </div>
            ${this.activeTab === 'register' ? html`
              <div class="form-group">
                <label for="rf-auth-email">Email</label>
                <input id="rf-auth-email" type="email" .value=${this.email} autocomplete="email"
                  @input=${(e: Event) => { this.email = (e.target as HTMLInputElement).value; }} required />
              </div>
            ` : ''}
            <div class="form-group">
              <label for="rf-auth-password">Password</label>
              <input id="rf-auth-password" type="password" .value=${this.password} autocomplete="current-password"
                @input=${(e: Event) => { this.password = (e.target as HTMLInputElement).value; }} required />
            </div>
            ${this.activeTab === 'register' ? html`
              <div class="form-group">
                <label for="rf-auth-confirm-password">Confirm Password</label>
                <input id="rf-auth-confirm-password" type="password" .value=${this.confirmPassword} autocomplete="new-password"
                  @input=${(e: Event) => { this.confirmPassword = (e.target as HTMLInputElement).value; }} required />
              </div>
            ` : ''}
            <button type="submit" class="submit-btn" ?disabled=${this.isLoading}>
              ${this.isLoading ? 'Processing...' : this.activeTab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
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
