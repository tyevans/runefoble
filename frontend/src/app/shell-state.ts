/**
 * App Shell State Sync (TASK-0640b).
 *
 * Applies the stored theme to the document and mirrors the signed-in user onto
 * the host. Plugin slots register again when the user changes.
 */

import type { CampaignItem } from '@runefoble/game-session-ui';
import type { AuthState } from '../auth/auth-service.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import type { CampaignCapabilities } from '../services/campaign-capabilities.ts';
import { registerDefaultPlugins, pluginRegistry } from '../components/plugins/plugin_registry.ts';

/** Reads the stored theme and color mode, then sets them on the document root. */
export function initTheme(host: RunefobleApp): void {
  try {
    host.currentTheme = window?.localStorage?.getItem('runefoble-theme') || host.currentTheme;
    host.currentColorMode = (window?.localStorage?.getItem('runefoble-color-mode') as any) || host.currentColorMode;
  } catch { /* storage restricted */ }
  document?.documentElement?.setAttribute('data-theme', host.currentTheme);
  document?.documentElement?.setAttribute('data-color-mode', host.currentColorMode);
}

/**
 * Copies the signed-in user id to the host. Role names never grant DM controls (ADR-0015 d).
 * A change of user drops the open campaign, so the flags of the previous user never linger.
 */
export function syncAuthState(host: RunefobleApp, s: AuthState): void {
  const userId = s.user?.user_id || '';
  if (host.currentUserId !== userId) setCurrentCampaign(host, null);
  host.currentUserId = userId;
}

/**
 * Sets the open campaign. The header shows the campaign role as text. The capability flags
 * belong to one campaign, so a change of campaign drops them until the loader sets new ones.
 */
export function setCurrentCampaign(host: RunefobleApp, campaign: CampaignItem | null): void {
  const changed = host.currentCampaign?.id !== campaign?.id;
  host.currentCampaign = campaign;
  host.userRole = campaign?.role || 'Player';
  if (changed) setCampaignCapabilities(host, null);
}

/**
 * Sets the caller's capability flags for the open campaign (TASK-0559). The view gates read
 * these flags. The DM-only plugins register when `run_session` is true.
 */
export function setCampaignCapabilities(host: RunefobleApp, capabilities: CampaignCapabilities | null): void {
  host.campaignCapabilities = capabilities;
  registerDefaultPlugins(pluginRegistry, Boolean(capabilities?.run_session));
}
