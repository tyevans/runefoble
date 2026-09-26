import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { settingsModalStyles } from './runefoble-settings-modal.styles.ts';
import { type ColorMode, type ThemeOption, SETTINGS_THEME_OPTIONS } from './runefoble-settings-modal.types.ts';
import type { ThemeMode } from './runefoble-theme-switcher.ts';
import { ThemeSettingsController } from './settings/settings-theme-controller.ts';
import './settings/runefoble-settings-appearance.ts';
import './settings/runefoble-settings-audio.ts';
import './settings/runefoble-settings-dice.ts';

export type { ColorMode, ThemeOption };
export { SETTINGS_THEME_OPTIONS };
export * from './settings/settings-theme-controller.ts';
export * from './settings/runefoble-settings-appearance.ts';
export * from './settings/runefoble-settings-audio.ts';
export * from './settings/runefoble-settings-dice.ts';

@customElement('runefoble-settings-modal')
export class RunefobleSettingsModal extends LitElement {
  static styles = settingsModalStyles;

  @property({ type: Boolean, reflect: true }) open: boolean = false;
  @property({ type: String }) currentTheme: ThemeMode = 'bauhaus';
  @property({ type: String }) currentColorMode: ColorMode = 'system';

  @state() private activeTab: 'appearance' | 'audio' | 'dice' = 'appearance';
  @state() private audioInputDevice = 'default';
  @state() private noiseSuppression = true;
  @state() private dicePhysics = true;
  @state() private diceSound = true;

  private themeCtrl = new ThemeSettingsController(this);
  private triggerElement: HTMLElement | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    if (this.currentTheme !== 'bauhaus') this.themeCtrl.currentTheme = this.currentTheme;
    if (this.currentColorMode !== 'system') this.themeCtrl.currentColorMode = this.currentColorMode;
    window.addEventListener('keydown', this.handleKeyDown);
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this.handleKeyDown);
  }

  updated(changed: Map<string, any>): void {
    if (changed.has('open')) {
      if (this.open) {
        this.triggerElement = document.activeElement as HTMLElement | null;
        this.updateComplete.then(() => (this.shadowRoot?.querySelector('.close-btn') as HTMLElement)?.focus());
      } else if (changed.get('open') === true) { this.triggerElement?.focus(); }
    }
    if (changed.has('currentTheme')) this.themeCtrl.currentTheme = this.currentTheme;
    if (changed.has('currentColorMode')) this.themeCtrl.currentColorMode = this.currentColorMode;
  }

  public openModal(): void { this.open = true; }
  public closeModal(): void {
    this.open = false;
    this.dispatchEvent(new CustomEvent('settings-closed', { bubbles: true, composed: true }));
  }

  public setColorMode(mode: ColorMode): void { this.currentColorMode = mode; this.themeCtrl.setColorMode(mode); }
  public setTheme(theme: ThemeMode): void { this.currentTheme = theme; this.themeCtrl.setTheme(theme); }

  private handleKeyDown = (e: KeyboardEvent): void => {
    if (!this.open) return;
    if (e.key === 'Escape') { e.preventDefault(); this.closeModal(); }
    else if (e.key === 'Tab') { this.handleFocusTrap(e); }
  };

  private handleFocusTrap(e: KeyboardEvent): void {
    const focusable = this.shadowRoot?.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex="0"], select, input');
    if (!focusable?.length) return;
    const [first, last] = [focusable[0], focusable[focusable.length - 1]];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  private renderTabContent() {
    if (this.activeTab === 'appearance') {
      return html`<runefoble-settings-appearance .currentTheme=${this.currentTheme} .currentColorMode=${this.currentColorMode}
        @theme-change=${(e: CustomEvent) => this.setTheme(e.detail.theme)}
        @color-mode-change=${(e: CustomEvent) => this.setColorMode(e.detail.mode)}></runefoble-settings-appearance>`;
    }
    if (this.activeTab === 'audio') {
      return html`<runefoble-settings-audio .audioInputDevice=${this.audioInputDevice} .noiseSuppression=${this.noiseSuppression}
        @device-change=${(e: CustomEvent) => { this.audioInputDevice = e.detail.device; }}
        @noise-suppression-change=${(e: CustomEvent) => { this.noiseSuppression = e.detail.noiseSuppression; }}></runefoble-settings-audio>`;
    }
    return html`<runefoble-settings-dice .dicePhysics=${this.dicePhysics} .diceSound=${this.diceSound}
      @dice-physics-change=${(e: CustomEvent) => { this.dicePhysics = e.detail.dicePhysics; }}
      @dice-sound-change=${(e: CustomEvent) => { this.diceSound = e.detail.diceSound; }}></runefoble-settings-dice>`;
  }

  private handleBackdropClick(e: MouseEvent): void {
    if (e.target === e.currentTarget) this.closeModal();
  }

  render() {
    if (!this.open) return html``;
    return html`
      <div class="modal-overlay" @click=${this.handleBackdropClick} aria-hidden="${!this.open}">
        <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="settings-modal-title">
          <header class="modal-header">
            <div class="modal-title-group">
              <span class="modal-icon-badge" aria-hidden="true">⚙️</span>
              <h2 id="settings-modal-title" class="modal-title">Settings</h2>
            </div>
            <button class="close-btn" aria-label="Close settings" @click=${this.closeModal}>✖</button>
          </header>
          <nav class="nav-tabs" role="tablist" aria-label="Settings categories">
            <button role="tab" class="tab-btn ${this.activeTab === 'appearance' ? 'active' : ''}"
              aria-selected="${this.activeTab === 'appearance'}" @click=${() => { this.activeTab = 'appearance'; }}><span>🎨</span> Appearance & Theme</button>
            <button role="tab" class="tab-btn ${this.activeTab === 'audio' ? 'active' : ''}"
              aria-selected="${this.activeTab === 'audio'}" @click=${() => { this.activeTab = 'audio'; }}><span>🎙️</span> Audio & Voice Input</button>
            <button role="tab" class="tab-btn ${this.activeTab === 'dice' ? 'active' : ''}"
              aria-selected="${this.activeTab === 'dice'}" @click=${() => { this.activeTab = 'dice'; }}><span>🎲</span> Dice & Physics</button>
          </nav>
          <div class="modal-body">${this.renderTabContent()}</div>
          <footer class="modal-footer">
            <span class="status-text">Theme: <strong>${this.currentTheme}</strong> • Mode: <strong>${this.currentColorMode}</strong></span>
            <button class="done-btn" @click=${this.closeModal}>Done</button>
          </footer>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-settings-modal': RunefobleSettingsModal;
  }
}
