import type { ReactiveController, ReactiveControllerHost } from 'lit';
import type { ThemeMode } from '../runefoble-theme-switcher.ts';
import type { ColorMode } from '../runefoble-settings-modal.types.ts';

export class ThemeSettingsController implements ReactiveController {
  host: ReactiveControllerHost & HTMLElement;
  currentTheme: ThemeMode = 'bauhaus';
  currentColorMode: ColorMode = 'system';
  resolvedColorMode: 'light' | 'dark' = 'light';
  private mediaQuery: MediaQueryList | null = null;
  private boundMediaHandler: ((e: MediaQueryListEvent) => void) | null = null;

  constructor(host: ReactiveControllerHost & HTMLElement) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {
    this.initStoredSettings();
    this.setupMediaQuery();
  }

  hostDisconnected(): void {
    if (this.mediaQuery && this.boundMediaHandler) {
      if (this.mediaQuery.removeEventListener) {
        this.mediaQuery.removeEventListener('change', this.boundMediaHandler);
      } else if ('removeListener' in this.mediaQuery) {
        (this.mediaQuery as any).removeListener(this.boundMediaHandler);
      }
    }
  }

  private initStoredSettings(): void {
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

  private setupMediaQuery(): void {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.boundMediaHandler = (e: MediaQueryListEvent) => {
      if (this.currentColorMode === 'system') {
        const resolved = e.matches ? 'dark' : 'light';
        this.resolvedColorMode = resolved;
        this.dispatchColorModeEvent('system', resolved);
        this.host.requestUpdate();
      }
    };
    if (this.mediaQuery.addEventListener) {
      this.mediaQuery.addEventListener('change', this.boundMediaHandler);
    } else if ('addListener' in this.mediaQuery) {
      (this.mediaQuery as any).addListener(this.boundMediaHandler);
    }
  }

  updateResolvedMode(): void {
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

  setColorMode(mode: ColorMode): void {
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
    this.host.requestUpdate();
  }

  setTheme(theme: ThemeMode): void {
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
    this.host.dispatchEvent(
      new CustomEvent('theme-changed', {
        detail: { theme },
        bubbles: true,
        composed: true,
      })
    );
    this.host.requestUpdate();
  }

  private dispatchColorModeEvent(mode: ColorMode, resolvedMode: 'light' | 'dark'): void {
    this.host.dispatchEvent(
      new CustomEvent('color-mode-changed', {
        detail: { mode, resolvedMode },
        bubbles: true,
        composed: true,
      })
    );
  }
}
