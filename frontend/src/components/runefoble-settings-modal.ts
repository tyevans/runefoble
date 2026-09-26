import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { settingsModalStyles } from './runefoble-settings-modal.styles.ts';
import {
  type ColorMode,
  type ThemeOption,
  SETTINGS_THEME_OPTIONS,
} from './runefoble-settings-modal.types.ts';
import type { ThemeMode } from './runefoble-theme-switcher.ts';

export type { ColorMode, ThemeOption };
export { SETTINGS_THEME_OPTIONS };

@customElement('runefoble-settings-modal')
export class RunefobleSettingsModal extends LitElement {
  static styles = settingsModalStyles;

  @property({ type: Boolean, reflect: true }) open: boolean = false;
  @property({ type: String }) currentTheme: ThemeMode = 'bauhaus';
  @property({ type: String }) currentColorMode: ColorMode = 'system';

  @state() private activeTab: 'appearance' | 'audio' | 'dice' = 'appearance';
  @state() private resolvedColorMode: 'light' | 'dark' = 'light';
  @state() private audioInputDevice: string = 'default';
  @state() private noiseSuppression: boolean = true;
  @state() private dicePhysics: boolean = true;
  @state() private diceSound: boolean = true;

  private triggerElement: HTMLElement | null = null;
  private mediaQuery: MediaQueryList | null = null;
  private boundMediaHandler: ((e: MediaQueryListEvent) => void) | null = null;

  connectedCallback() {
    super.connectedCallback();
    this.initStoredSettings();
    this.setupMediaQuery();
    window.addEventListener('keydown', this.handleKeyDown);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this.handleKeyDown);
    if (this.mediaQuery && this.boundMediaHandler) {
      if (this.mediaQuery.removeEventListener) {
        this.mediaQuery.removeEventListener('change', this.boundMediaHandler);
      } else if ('removeListener' in this.mediaQuery) {
        (this.mediaQuery as any).removeListener(this.boundMediaHandler);
      }
    }
  }

  updated(changedProps: Map<string, any>) {
    if (changedProps.has('open')) {
      if (this.open) {
        this.triggerElement = document.activeElement as HTMLElement | null;
        this.updateComplete.then(() => {
          const closeBtn = this.shadowRoot?.querySelector('.close-btn') as HTMLElement;
          closeBtn?.focus();
        });
      } else if (changedProps.get('open') === true) {
        this.triggerElement?.focus();
      }
    }
  }

  private initStoredSettings() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const storedTheme = window.localStorage.getItem('runefoble-theme');
        if (storedTheme && ['bauhaus', 'dark-fantasy', 'parchment', 'cyber-rune'].includes(storedTheme)) {
          this.currentTheme = storedTheme as ThemeMode;
        }
        const storedMode = window.localStorage.getItem('runefoble-color-mode');
        if (storedMode && ['light', 'dark', 'system'].includes(storedMode)) {
          this.currentColorMode = storedMode as ColorMode;
        }
      }
    } catch {
      // Storage access may be restricted
    }
    this.updateResolvedMode();
  }

  private setupMediaQuery() {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.boundMediaHandler = (e: MediaQueryListEvent) => {
      if (this.currentColorMode === 'system') {
        const resolved = e.matches ? 'dark' : 'light';
        this.resolvedColorMode = resolved;
        this.dispatchColorModeEvent('system', resolved);
      }
    };
    if (this.mediaQuery.addEventListener) {
      this.mediaQuery.addEventListener('change', this.boundMediaHandler);
    } else if ('addListener' in this.mediaQuery) {
      (this.mediaQuery as any).addListener(this.boundMediaHandler);
    }
  }

  private updateResolvedMode() {
    if (this.currentColorMode === 'system') {
      const prefersDark =
        typeof window !== 'undefined' &&
        window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.resolvedColorMode = prefersDark ? 'dark' : 'light';
    } else {
      this.resolvedColorMode = this.currentColorMode;
    }
  }

  public openModal() {
    this.open = true;
  }

  public closeModal() {
    this.open = false;
    this.dispatchEvent(
      new CustomEvent('settings-closed', {
        bubbles: true,
        composed: true,
      })
    );
  }

  public setColorMode(mode: ColorMode) {
    this.currentColorMode = mode;
    this.updateResolvedMode();
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.setAttribute('data-color-mode', mode);
    }
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('runefoble-color-mode', mode);
      }
    } catch {
      // Ignore storage errors
    }
    this.dispatchColorModeEvent(mode, this.resolvedColorMode);
  }

  public setTheme(theme: ThemeMode) {
    this.currentTheme = theme;
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.setAttribute('data-theme', theme);
    }
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('runefoble-theme', theme);
      }
    } catch {
      // Ignore storage errors
    }
    this.dispatchEvent(
      new CustomEvent('theme-changed', {
        detail: { theme },
        bubbles: true,
        composed: true,
      })
    );
  }

  private dispatchColorModeEvent(mode: ColorMode, resolvedMode: 'light' | 'dark') {
    this.dispatchEvent(
      new CustomEvent('color-mode-changed', {
        detail: { mode, resolvedMode },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleKeyDown = (e: KeyboardEvent) => {
    if (!this.open) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      this.closeModal();
    } else if (e.key === 'Tab') {
      this.handleFocusTrap(e);
    }
  };

  private handleFocusTrap(e: KeyboardEvent) {
    const focusable = this.shadowRoot?.querySelectorAll(
      'button:not([disabled]), [tabindex="0"], select, input'
    );
    if (!focusable || focusable.length === 0) return;

    const first = focusable[0] as HTMLElement;
    const last = focusable[focusable.length - 1] as HTMLElement;

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  private handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      this.closeModal();
    }
  }

  render() {
    if (!this.open) {
      return html``;
    }

    return html`
      <div
        class="modal-overlay"
        @click=${this.handleBackdropClick}
        aria-hidden="${!this.open}"
      >
        <div
          class="modal-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="settings-modal-title"
        >
          <header class="modal-header">
            <div class="modal-title-group">
              <span class="modal-icon-badge" aria-hidden="true">⚙️</span>
              <h2 id="settings-modal-title" class="modal-title">Settings</h2>
            </div>
            <button
              class="close-btn"
              aria-label="Close settings"
              @click=${this.closeModal}
            >
              ✖
            </button>
          </header>

          <nav class="nav-tabs" role="tablist" aria-label="Settings categories">
            <button
              role="tab"
              class="tab-btn ${this.activeTab === 'appearance' ? 'active' : ''}"
              aria-selected="${this.activeTab === 'appearance'}"
              @click=${() => { this.activeTab = 'appearance'; }}
            >
              <span>🎨</span> Appearance & Theme
            </button>
            <button
              role="tab"
              class="tab-btn ${this.activeTab === 'audio' ? 'active' : ''}"
              aria-selected="${this.activeTab === 'audio'}"
              @click=${() => { this.activeTab = 'audio'; }}
            >
              <span>🎙️</span> Audio & Voice Input
            </button>
            <button
              role="tab"
              class="tab-btn ${this.activeTab === 'dice' ? 'active' : ''}"
              aria-selected="${this.activeTab === 'dice'}"
              @click=${() => { this.activeTab = 'dice'; }}
            >
              <span>🎲</span> Dice & Physics
            </button>
          </nav>

          <div class="modal-body">
            ${this.activeTab === 'appearance' ? this.renderAppearanceTab() : ''}
            ${this.activeTab === 'audio' ? this.renderAudioTab() : ''}
            ${this.activeTab === 'dice' ? this.renderDiceTab() : ''}
          </div>

          <footer class="modal-footer">
            <span class="status-text">
              Theme: <strong>${this.currentTheme}</strong> • Mode: <strong>${this.currentColorMode}</strong>
            </span>
            <button class="done-btn" @click=${this.closeModal}>
              Done
            </button>
          </footer>
        </div>
      </div>
    `;
  }

  private renderAppearanceTab() {
    return html`
      <div>
        <h3 class="section-title"><span>☀️</span> Color Mode</h3>
        <div class="segmented-group" role="radiogroup" aria-label="Appearance color mode">
          <button
            type="button"
            class="segment-btn ${this.currentColorMode === 'light' ? 'active' : ''}"
            aria-pressed="${this.currentColorMode === 'light'}"
            @click=${() => this.setColorMode('light')}
          >
            <span>☀️</span> Light
          </button>
          <button
            type="button"
            class="segment-btn ${this.currentColorMode === 'dark' ? 'active' : ''}"
            aria-pressed="${this.currentColorMode === 'dark'}"
            @click=${() => this.setColorMode('dark')}
          >
            <span>🌙</span> Dark
          </button>
          <button
            type="button"
            class="segment-btn ${this.currentColorMode === 'system' ? 'active' : ''}"
            aria-pressed="${this.currentColorMode === 'system'}"
            @click=${() => this.setColorMode('system')}
          >
            <span>💻</span> System
          </button>
        </div>
      </div>

      <div>
        <h3 class="section-title"><span>🎨</span> Theme & Aesthetic</h3>
        <div class="theme-grid">
          ${SETTINGS_THEME_OPTIONS.map(
            (opt) => html`
              <button
                type="button"
                class="theme-card ${this.currentTheme === opt.id ? 'active' : ''}"
                aria-pressed="${this.currentTheme === opt.id}"
                @click=${() => this.setTheme(opt.id)}
              >
                <div class="theme-card-header">
                  <span class="theme-card-title">
                    <span>${opt.badge}</span> ${opt.name}
                  </span>
                  ${this.currentTheme === opt.id
                    ? html`<span class="active-tag">Active</span>`
                    : ''}
                </div>
                <p class="theme-desc">${opt.description}</p>
                <div class="swatch-group" aria-label="Palette colors for ${opt.name}">
                  ${opt.swatches.map(
                    (color) => html`
                      <span class="swatch-chip" style="background-color: ${color};"></span>
                    `
                  )}
                </div>
              </button>
            `
          )}
        </div>
      </div>
    `;
  }

  private renderAudioTab() {
    return html`
      <div class="form-group">
        <label class="form-label" for="audio-input-device">Microphone Input Device</label>
        <select
          id="audio-input-device"
          class="form-select"
          .value=${this.audioInputDevice}
          @change=${(e: Event) => {
            this.audioInputDevice = (e.target as HTMLSelectElement).value;
          }}
        >
          <option value="default">Default System Microphone</option>
          <option value="studio-mic">Studio Condenser Mic (USB Audio)</option>
          <option value="headset">Gaming Headset Microphone</option>
        </select>
      </div>

      <div class="form-group">
        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.noiseSuppression}
            @change=${(e: Event) => {
              this.noiseSuppression = (e.target as HTMLInputElement).checked;
            }}
          />
          Adaptive Noise Suppression & Echo Cancellation
        </label>
      </div>
    `;
  }

  private renderDiceTab() {
    return html`
      <div class="form-group">
        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.dicePhysics}
            @change=${(e: Event) => {
              this.dicePhysics = (e.target as HTMLInputElement).checked;
            }}
          />
          Enable 3D Kinetic Dice Physics Simulation
        </label>
      </div>

      <div class="form-group">
        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.diceSound}
            @change=${(e: Event) => {
              this.diceSound = (e.target as HTMLInputElement).checked;
            }}
          />
          Dice Rolling Spatial Foley Audio
        </label>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-settings-modal': RunefobleSettingsModal;
  }
}
