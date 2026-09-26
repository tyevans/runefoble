import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { settingsModalStyles } from '../runefoble-settings-modal.styles.ts';
import {
  type ColorMode,
  type ThemeOption,
  SETTINGS_THEME_OPTIONS,
} from '../runefoble-settings-modal.types.ts';
import type { ThemeMode } from '../runefoble-theme-switcher.ts';

@customElement('runefoble-settings-appearance')
export class RunefobleSettingsAppearance extends LitElement {
  static styles = settingsModalStyles;

  @property({ type: String }) currentTheme: ThemeMode = 'bauhaus';
  @property({ type: String }) currentColorMode: ColorMode = 'system';

  setColorMode(mode: ColorMode): void {
    this.dispatchEvent(
      new CustomEvent('color-mode-change', {
        detail: { mode },
        bubbles: true,
        composed: true,
      })
    );
  }

  setTheme(theme: ThemeMode): void {
    this.dispatchEvent(
      new CustomEvent('theme-change', {
        detail: { theme },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
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
            (opt: ThemeOption) => html`
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
                    (color: string) => html`
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
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-settings-appearance': RunefobleSettingsAppearance;
  }
}
