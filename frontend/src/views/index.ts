/**
 * View Controller Registry (TASK-0643).
 *
 * One controller per route view. A controller renders its view and loads its data.
 * The shell and the data loader look the controller up by view id.
 */

import { html, type TemplateResult } from 'lit';
import type { MatchedRoute } from '../router/index.ts';
import type { AppActiveView } from '../router/view-resolver.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { loadActiveSessionData, loadLobbyData } from '../app/session-data-loader.ts';
import { loadDashboardData, renderDashboard } from './campaign-dashboard-view.ts';
import { loadCampaignHubData, renderCampaignHub } from './campaign-hub-view.ts';
import { loadCharacterSheet, loadRoster, renderCharacterSheet, renderRoster } from './character-view.ts';
import { renderLobby } from './lobby-view.ts';
import { renderProfile } from './profile-view.ts';
import { renderSessionActive } from './session-view.ts';

export interface ViewController {
  render(app: RunefobleApp, view: AppActiveView): TemplateResult;
  /** Loads the data for the view. A view with no data omits it. */
  load?(app: RunefobleApp, route: MatchedRoute): Promise<void>;
  /** The header campaign switcher loads for this view. */
  switcher: boolean;
}

const hub: ViewController = { render: renderCampaignHub, load: loadCampaignHubData, switcher: true };

export const VIEW_CONTROLLERS: Record<AppActiveView, ViewController> = {
  'login': { render: renderAuthFallback, switcher: false },
  'campaigns': { render: renderDashboard, load: loadDashboardData, switcher: false },
  'campaign-detail': hub,
  'campaign-characters': hub,
  'campaign-codex': hub,
  'campaign-analytics': hub,
  'characters': { render: renderRoster, load: loadRoster, switcher: true },
  'character-sheet': { render: renderCharacterSheet, load: loadCharacterSheet, switcher: true },
  'session-lobby': { render: renderLobby, load: loadLobbyData, switcher: true },
  'session-active': { render: renderSessionActive, load: loadActiveSessionData, switcher: true },
  'profile': { render: renderProfile, switcher: true },
};

function renderAuthFallback(): TemplateResult {
  return html`<div class="auth-fallback-view"><h2>Authentication Portal</h2><p>Log in or create a Runefoble adventurer account to continue.</p></div>`;
}
