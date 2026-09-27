/**
 * Runefoble User Avatar & Dropdown Menu Component
 * ADR-0004, ADR-0012, ADR-0013, TASK-0207
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { router } from '../router/router.ts';

@customElement('runefoble-user-menu')
export class RunefobleUserMenu extends LitElement {
  @property({ type: Object }) user: UserClaims | null = null;
  @state() private isOpen = false;
  private unlistenAuth: (() => void) | null = null;

  static styles = css`
    :host { display: inline-block; position: relative; }
    .btn-signin {
      background: var(--rf-accent-primary, #e63946); color: #fff;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-weight: 800; font-size: 0.8rem; padding: 4px 12px; cursor: pointer;
      text-transform: uppercase; letter-spacing: 0.5px;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .btn-signin:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow, 4px 4px 0px #121212); }
    .avatar-btn {
      display: inline-flex; align-items: center; gap: 8px; background: var(--rf-bg-surface, #fff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      padding: 3px 8px; cursor: pointer; font-weight: 700; font-size: 0.85rem;
      color: var(--rf-text-primary, #121212);
    }
    .avatar-btn:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow, 4px 4px 0px #121212); }
    .avatar-circle {
      width: 24px; height: 24px; border-radius: 50%;
      background: var(--rf-accent-secondary, #1d3557); color: #fff;
      display: flex; align-items: center; justify-content: center;
      font-size: 0.75rem; font-weight: 800;
    }
    .dropdown {
      position: absolute; top: calc(100% + 6px); right: 0; min-width: 220px;
      background: var(--rf-bg-surface, #fff); color: var(--rf-text-primary, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      padding: 12px; z-index: var(--rf-z-dropdown, 500); display: flex; flex-direction: column; gap: 10px;
    }
    .user-info { display: flex; flex-direction: column; gap: 2px; border-bottom: 1px solid var(--rf-border-subtle, #d1d5db); padding-bottom: 8px; }
    .name { font-weight: 800; font-size: 0.95rem; }
    .email { font-size: 0.75rem; color: var(--rf-text-muted, #4b5563); word-break: break-all; }
    .roles-list { display: flex; flex-wrap: wrap; gap: 4px; }
    .role-badge {
      font-size: 0.65rem; font-weight: 800; text-transform: uppercase;
      padding: 1px 6px; background: var(--rf-bg-inset, #f1f3f5);
      border: 1px solid var(--rf-border-color, #121212);
    }
    .menu-actions { display: flex; flex-direction: column; gap: 6px; }
    .menu-item {
      background: none; border: 1px solid transparent; padding: 6px 8px;
      font-weight: 700; font-size: 0.85rem; text-align: left; cursor: pointer;
      color: var(--rf-text-primary, #121212); display: flex; align-items: center; gap: 8px;
    }
    .menu-item:hover { background: var(--rf-bg-inset, #f1f3f5); border-color: var(--rf-border-color, #121212); }
    .menu-item.signout { color: var(--rf-accent-primary, #e63946); }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (!this.user) this.user = authService.getUser();
    this.unlistenAuth = authService.onAuthChanged((st) => { this.user = st.user; });
    window.addEventListener('click', this.handleWindowClick);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.unlistenAuth) this.unlistenAuth();
    window.removeEventListener('click', this.handleWindowClick);
  }

  private handleWindowClick = (e: MouseEvent) => {
    if (this.isOpen && !this.contains(e.target as Node)) {
      this.isOpen = false;
    }
  };

  private handleOpenLogin() {
    this.dispatchEvent(new CustomEvent('open-login', { bubbles: true, composed: true }));
  }

  private handleToggleDropdown(e: MouseEvent) {
    e.stopPropagation();
    this.isOpen = !this.isOpen;
  }

  private handleAccountSettings() {
    this.isOpen = false;
    router.navigate('#/profile');
    this.dispatchEvent(new CustomEvent('navigate-profile', { bubbles: true, composed: true }));
  }

  private handleSignOut() {
    this.isOpen = false;
    authService.logout();
    this.dispatchEvent(new CustomEvent('auth-logout', { bubbles: true, composed: true }));
    router.navigate('#/login');
  }

  private getInitials(name: string): string {
    return (name || 'A').slice(0, 2).toUpperCase();
  }

  render() {
    if (!this.user) {
      return html`
        <button class="btn-signin" aria-label="Sign In" @click=${this.handleOpenLogin}>
          Sign In
        </button>
      `;
    }

    return html`
      <button class="avatar-btn" aria-haspopup="true" aria-expanded="${this.isOpen}"
        aria-label="User menu for ${this.user.username}" @click=${this.handleToggleDropdown}>
        <div class="avatar-circle">${this.getInitials(this.user.username)}</div>
        <span class="user-display-name">${this.user.username}</span>
        <span aria-hidden="true">▾</span>
      </button>

      ${this.isOpen ? html`
        <div class="dropdown" role="menu" aria-label="User Options">
          <div class="user-info">
            <span class="name">${this.user.username}</span>
            ${this.user.email ? html`<span class="email">${this.user.email}</span>` : ''}
            <div class="roles-list">
              ${(this.user.roles || []).map((r) => html`<span class="role-badge">${r}</span>`)}
            </div>
          </div>
          <div class="menu-actions">
            <button class="menu-item" role="menuitem" @click=${this.handleCharacterRoster}>
              <span>⚔️</span> Character Roster
            </button>
            <button class="menu-item" role="menuitem" @click=${this.handleAccountSettings}>
              <span>⚙️</span> Account Settings
            </button>
            <button class="menu-item signout" role="menuitem" @click=${this.handleSignOut}>
              <span>🚪</span> Sign Out
            </button>
          </div>
        </div>
      ` : ''}
    `;
  }

  private handleCharacterRoster() {
    this.isOpen = false;
    router.navigate('#/characters');
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-user-menu': RunefobleUserMenu;
  }
}
