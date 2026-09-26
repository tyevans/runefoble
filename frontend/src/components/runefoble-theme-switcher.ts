import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export type ThemeMode = 'bauhaus' | 'dark-fantasy' | 'parchment' | 'cyber-rune';

export interface ThemeItem {
  id: ThemeMode;
  name: string;
  badge: string;
}

export const THEME_OPTIONS: ThemeItem[] = [
  { id: 'bauhaus', name: 'Bauhaus', badge: '📐' },
  { id: 'dark-fantasy', name: 'Dark Fantasy', badge: '⚔️' },
  { id: 'parchment', name: 'Parchment', badge: '📜' },
  { id: 'cyber-rune', name: 'Cyber Rune', badge: '⚡' },
];

@customElement('runefoble-theme-switcher')
export class RunefobleThemeSwitcher extends LitElement {
  static styles = css`
    :host {
      display: inline-flex;
      align-items: center;
      font-family: var(--rf-font-family, system-ui, sans-serif);
      box-sizing: border-box;
    }

    .switcher-wrapper {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px;
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    }

    .switcher-label {
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--rf-text-muted, #4b5563);
      padding: 0 4px;
    }

    .buttons-group {
      display: inline-flex;
      gap: 4px;
    }

    .theme-button {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 5px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      border-radius: var(--rf-border-radius, 0px);
      background: var(--rf-bg-surface, #ffffff);
      color: var(--rf-text-primary, #121212);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
      transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.15s ease;
    }

    .theme-button:hover:not(.active) {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }

    .theme-button.active {
      background: var(--rf-color-yellow, #ffb703);
      color: #121212;
      font-weight: 800;
      border-color: var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    }

    .theme-button.active.bauhaus {
      background: var(--rf-color-yellow, #ffb703);
    }

    .theme-button.active.dark-fantasy {
      background: var(--rf-accent-primary, #f59e0b);
    }

    .theme-button.active.parchment {
      background: var(--rf-accent-secondary, #bb8524);
      color: #2e1b0f;
    }

    .theme-button.active.cyber-rune {
      background: var(--rf-accent-primary, #06b6d4);
      color: #09090b;
    }

    .theme-button:active {
      transform: translate(2px, 2px);
      box-shadow: 0px 0px 0px #121212;
    }

    .theme-icon {
      font-size: 0.8rem;
    }
  `;

  @property({ type: String }) currentTheme: ThemeMode = 'bauhaus';

  connectedCallback() {
    super.connectedCallback();
    const stored = this.getStoredTheme();
    if (stored) {
      this.currentTheme = stored;
    }
    this.applyTheme(this.currentTheme, false);
  }

  private getStoredTheme(): ThemeMode | null {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const item = window.localStorage.getItem('runefoble-theme');
        if (item && ['bauhaus', 'dark-fantasy', 'parchment', 'cyber-rune'].includes(item)) {
          return item as ThemeMode;
        }
      }
    } catch {
      // LocalStorage access may fail in restricted contexts
    }
    return null;
  }

  public setTheme(theme: ThemeMode) {
    this.currentTheme = theme;
    this.applyTheme(theme, true);
  }

  private applyTheme(theme: ThemeMode, emitEvent: boolean) {
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

    if (emitEvent) {
      this.dispatchEvent(
        new CustomEvent('theme-changed', {
          detail: { theme },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  render() {
    return html`
      <div class="switcher-wrapper" role="toolbar" aria-label="Theme selector">
        <span class="switcher-label">Theme:</span>
        <div class="buttons-group">
          ${THEME_OPTIONS.map(
            (opt) => html`
              <button
                type="button"
                class="theme-button ${this.currentTheme === opt.id ? `active ${opt.id}` : ''}"
                aria-pressed="${this.currentTheme === opt.id ? 'true' : 'false'}"
                @click=${() => this.setTheme(opt.id)}
              >
                <span class="theme-icon">${opt.badge}</span>
                <span>${opt.name}</span>
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
    'runefoble-theme-switcher': RunefobleThemeSwitcher;
  }
}
