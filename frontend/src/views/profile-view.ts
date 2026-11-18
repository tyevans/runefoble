/**
 * Profile View (TASK-0643). Renders the account settings. The profile component reads its own data.
 */

import { html } from 'lit';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';

export function renderProfile(app: RunefobleApp) {
  return html`<runefoble-user-profile .currentTheme=${app.currentTheme} .currentColorMode=${app.currentColorMode} @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) app.currentTheme = e.detail.theme; }} @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) app.currentColorMode = e.detail.mode; }} @auth-logout=${() => router.navigate('#/login')}></runefoble-user-profile>`;
}
