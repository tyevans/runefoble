/**
 * App Shell Frame Template (TASK-0640b).
 *
 * Renders the chrome around the routed view: header, main region, toast, settings modal,
 * auth modal, and the absentee overlays.
 */

import { html } from 'lit';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { renderAbsenteeOverlays } from './session-view-templates.ts';
import { renderActiveView } from './view-templates.ts';

export function renderAppShell(app: RunefobleApp) {
  const view = app.getActiveView();
  return html`<runefoble-header data-route=${app.currentRoute?.pattern || ''} data-view=${view} data-params=${JSON.stringify(app.routeParams)} .viewMode=${app.viewMode} .isSettingsOpen=${app.isSettingsOpen} .socketConnected=${app.socketConnected} .campaignId=${app.campaignId} .sessionId=${app.sessionId} .userRole=${app.userRole} .breadcrumbs=${app.breadcrumbs} @open-settings=${() => { app.isSettingsOpen = true; }} @open-login=${() => { app.authInitialTab = 'login'; app.isAuthModalOpen = true; }} @toggle-view-mode=${(e: CustomEvent) => { app.viewMode = e.detail.viewMode; }} @campaign-changed=${(e: CustomEvent) => { app.campaignId = e.detail.campaignId; router.navigate('#/campaigns/' + e.detail.campaignId); }}></runefoble-header>
    <main class="app-content" data-active-view=${view}>${renderActiveView(app, view)}</main>
    ${app.toastMessage ? html`<div class="toast-notification" role="status" aria-live="polite">${app.toastMessage}</div>` : ''}
    <runefoble-settings-modal .open=${app.isSettingsOpen} .currentTheme=${app.currentTheme} .currentColorMode=${app.currentColorMode} @settings-closed=${app.handleSettingsClosed} @theme-changed=${(e: CustomEvent) => { if (e.detail?.theme) app.currentTheme = e.detail.theme; }} @color-mode-changed=${(e: CustomEvent) => { if (e.detail?.mode) app.currentColorMode = e.detail.mode; }}></runefoble-settings-modal>
    <runefoble-auth-modal .open=${app.isAuthModalOpen || view === 'login'} .initialTab=${app.authInitialTab} @auth-modal-closed=${() => { app.isAuthModalOpen = false; if (app.currentRoute?.pattern === '#/login' || app.currentRoute?.pattern === '#/register') router.navigate('#/campaigns'); }}></runefoble-auth-modal>
    ${renderAbsenteeOverlays(app)}`;
}
