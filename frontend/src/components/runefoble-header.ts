import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './runefoble-campaign-nav.ts';

@customElement('runefoble-header')
export class RunefobleHeader extends LitElement {
  @property({ type: String }) viewMode: 'party' | 'spectator' = 'party';
  @property({ type: Boolean }) isSettingsOpen = false;
  @property({ type: Boolean }) socketConnected = false;
  @property({ type: String }) campaignId = '4';
  @property({ type: String }) sessionId = '14';
  @property({ type: String }) dmName = 'The Watcher';
  @property({ type: String }) userRole = 'Player';

  static styles = css`
    :host { display: block; }
    header {
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 20px; border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      margin-bottom: 24px; flex-wrap: wrap; gap: 16px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand h1 { font-size: 1.9rem; margin: 0; color: var(--rf-text-primary, #121212); font-weight: 900; letter-spacing: -0.5px; }
    .tagline { font-size: 0.9rem; color: var(--rf-text-muted, #4b5563); }
    .header-actions { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
    .settings-trigger, .view-mode-btn {
      display: inline-flex; align-items: center; gap: 6px;
      background: var(--rf-bg-surface, #ffffff); color: var(--rf-text-primary, #121212);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      font-weight: 700; font-size: 0.8rem; padding: 4px 10px; cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .settings-trigger:hover, .view-mode-btn:hover {
      transform: translate(-1px, -1px); box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }
    .settings-trigger:active, .view-mode-btn:active {
      transform: translate(1px, 1px); box-shadow: 0px 0px 0px #121212;
    }
    @media (max-width: 640px) {
      .settings-label { display: none; }
    }
  `;

  private handleOpenSettings() {
    this.dispatchEvent(new CustomEvent('open-settings', { bubbles: true, composed: true }));
  }

  private handleToggleViewMode() {
    const nextMode = this.viewMode === 'party' ? 'spectator' : 'party';
    this.dispatchEvent(new CustomEvent('toggle-view-mode', {
      detail: { viewMode: nextMode }, bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <header>
        <div class="brand">
          <h1>Runefoble</h1>
          <span class="tagline">Imaginative Gaming for Storytellers</span>
        </div>
        <div class="header-actions">
          <button
            id="settings-trigger-btn"
            class="settings-trigger"
            aria-haspopup="dialog"
            aria-expanded="${this.isSettingsOpen ? 'true' : 'false'}"
            aria-label="Open settings"
            @click=${this.handleOpenSettings}
          >
            <span class="settings-icon" aria-hidden="true">⚙️</span>
            <span class="settings-label">Settings</span>
          </button>
          <button
            class="view-mode-btn"
            aria-label="Toggle view mode"
            @click=${this.handleToggleViewMode}
          >
            ${this.viewMode === 'party' ? '📺 Spectator Mode' : '🎮 Party Mode'}
          </button>
          <runefoble-campaign-nav
            .campaignId=${this.campaignId}
            .sessionId=${this.sessionId}
            .dmName=${this.dmName}
            .userRole=${this.userRole}
            .socketConnected=${this.socketConnected}
          ></runefoble-campaign-nav>
        </div>
      </header>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-header': RunefobleHeader;
  }
}
