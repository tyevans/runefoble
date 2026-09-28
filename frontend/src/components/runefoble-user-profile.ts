/**
 * Runefoble User Profile & Account Settings View Component
 * ADR-0004, ADR-0012, ADR-0013, TASK-0257
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { authService, type UserClaims } from '../auth/auth-service.ts';
import { router } from '../router/router.ts';
import './runefoble-theme-switcher.ts';
import type { ThemeMode } from './runefoble-theme-switcher.ts';
import { userProfileStyles } from './runefoble-user-profile.styles.ts';

@customElement('runefoble-user-profile')
export class RunefobleUserProfile extends LitElement {
  static styles = [userProfileStyles];

  @property({ type: Object }) user: UserClaims | null = null;
  @property({ type: String }) currentTheme: string = 'bauhaus';
  @property({ type: String }) currentColorMode: 'light' | 'dark' | 'system' = 'system';

  @state() private profileData: UserClaims | null = null;
  @state() private isLoading = false;
  private unlistenAuth: (() => void) | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.initPreferences();
    this.loadProfile();
    this.unlistenAuth = authService.onAuthChanged((st) => {
      if (st.user) {
        this.profileData = st.user;
        this.requestUpdate();
      }
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.unlistenAuth) {
      this.unlistenAuth();
      this.unlistenAuth = null;
    }
  }

  updated(changedProps: Map<string | number | symbol, unknown>) {
    if (changedProps.has('user') && this.user) {
      this.profileData = this.user;
    }
  }

  private initPreferences() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const storedTheme = window.localStorage.getItem('runefoble-theme');
        if (storedTheme) this.currentTheme = storedTheme;
        const storedMode = window.localStorage.getItem('runefoble-color-mode') as any;
        if (storedMode) this.currentColorMode = storedMode;
      }
    } catch { /* storage restricted */ }
  }

  public async loadProfile(): Promise<void> {
    if (this.user) {
      this.profileData = this.user;
      return;
    }
    const current = authService.getUser();
    if (current) {
      this.profileData = current;
    }
    try {
      this.isLoading = true;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      const token = authService.getAccessToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
      if (current?.user_id) headers['X-User-Id'] = current.user_id;

      const res = await fetch('/api/v1/profile', { headers });
      if (res.ok) {
        this.profileData = await res.json();
      }
    } catch {
      // Fallback preserved
    } finally {
      this.isLoading = false;
    }

    if (!this.profileData) {
      this.profileData = {
        user_id: 'user-valeros',
        username: 'Valeros',
        email: 'valeros@runefoble.local',
        roles: ['player'],
        is_admin: false,
      };
    }
  }

  private getEffectiveUser(): UserClaims {
    return (
      this.user ||
      this.profileData ||
      authService.getUser() || {
        user_id: 'user-valeros',
        username: 'Valeros',
        email: 'valeros@runefoble.local',
        roles: ['player'],
        is_admin: false,
      }
    );
  }

  private getInitials(name: string): string {
    return (name || 'A').slice(0, 2).toUpperCase();
  }

  private handleSignOut() {
    authService.logout();
    this.dispatchEvent(new CustomEvent('auth-logout', { bubbles: true, composed: true }));
    router.navigate('#/login');
  }

  private handleThemeChanged(e: CustomEvent<{ theme: ThemeMode }>) {
    if (e.detail?.theme) {
      this.currentTheme = e.detail.theme;
      this.dispatchEvent(
        new CustomEvent('theme-changed', {
          detail: { theme: this.currentTheme },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  private setColorMode(mode: 'light' | 'dark' | 'system') {
    this.currentColorMode = mode;
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('runefoble-color-mode', mode);
      }
    } catch { /* storage restricted */ }
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.setAttribute('data-color-mode', mode);
    }
    this.dispatchEvent(
      new CustomEvent('color-mode-changed', {
        detail: { mode },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const user = this.getEffectiveUser();
    const roles = user.roles || [];
    const isAdmin = Boolean(user.is_admin || roles.includes('admin'));

    return html`
      <div class="profile-card" data-testid="profile-settings-card" data-loading=${this.isLoading}>
        ${this.isLoading ? html`<div class="profile-loading" role="status" aria-live="polite">Loading adventurer profile...</div>` : ''}
        <header class="profile-header">
          <div class="user-identity">
            <div class="avatar-large" aria-hidden="true">${this.getInitials(user.username)}</div>
            <div class="identity-text">
              <h1 class="profile-title" data-testid="profile-username">${user.username}</h1>
              <span class="user-id-badge" data-testid="profile-user-id">ID: ${user.user_id}</span>
            </div>
          </div>
          <button class="btn-logout" type="button" @click=${this.handleSignOut} aria-label="Sign Out">
            <span>🚪</span> Sign Out
          </button>
        </header>

        <section class="claims-section">
          <h2 class="section-title"><span>🛡️</span> Identity & Account Claims</h2>
          <div class="claims-grid">
            <div class="claim-item">
              <span class="claim-label">Email Address</span>
              <span class="claim-value" data-testid="profile-email">${user.email || 'Not configured'}</span>
            </div>
            <div class="claim-item">
              <span class="claim-label">Assigned Roles</span>
              <div class="roles-list" data-testid="profile-roles">
                ${roles.length > 0
                  ? roles.map((r) => html`<span class="role-badge ${r.toLowerCase()}">${r}</span>`)
                  : html`<span class="claim-value">Adventurer</span>`}
                ${isAdmin ? html`<span class="role-badge admin">Admin</span>` : ''}
              </div>
            </div>
            <div class="claim-item">
              <span class="claim-label">Privilege Level</span>
              <span class="claim-value" data-testid="profile-admin-status">
                ${isAdmin ? 'Full Administrator (Zanzibar Superuser)' : 'Standard Adventurer'}
              </span>
            </div>
            <div class="claim-item">
              <span class="claim-label">Authentication Provider</span>
              <span class="claim-value">Zitadel OIDC (RS256 PKCE)</span>
            </div>
          </div>
        </section>

        <section class="preferences-section">
          <h2 class="section-title"><span>🎨</span> Appearance & Theme Selection</h2>
          <div class="controls-row">
            <div class="control-label-group">
              <span class="control-label">Design System Theme</span>
              <span class="control-desc">Select high-contrast Bauhaus or atmospheric tabletop styling</span>
            </div>
            <runefoble-theme-switcher
              .currentTheme=${this.currentTheme as ThemeMode}
              @theme-changed=${this.handleThemeChanged}
            ></runefoble-theme-switcher>
          </div>

          <div class="controls-row">
            <div class="control-label-group">
              <span class="control-label">Color Mode</span>
              <span class="control-desc">Choose between Light, Dark, or System adaptive palette</span>
            </div>
            <div class="color-mode-buttons" role="group" aria-label="Color mode selector">
              <button
                type="button"
                class="mode-btn ${this.currentColorMode === 'light' ? 'active' : ''}"
                @click=${() => this.setColorMode('light')}
              >
                Light
              </button>
              <button
                type="button"
                class="mode-btn ${this.currentColorMode === 'dark' ? 'active' : ''}"
                @click=${() => this.setColorMode('dark')}
              >
                Dark
              </button>
              <button
                type="button"
                class="mode-btn ${this.currentColorMode === 'system' ? 'active' : ''}"
                @click=${() => this.setColorMode('system')}
              >
                System
              </button>
            </div>
          </div>
        </section>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-user-profile': RunefobleUserProfile;
  }
}
