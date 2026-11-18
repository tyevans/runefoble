/**
 * App Shell State Sync (TASK-0640b).
 *
 * Applies the stored theme to the document and mirrors the signed-in user onto
 * the host. Plugin slots register again when the user changes.
 */

import type { CampaignItem } from '@runefoble/game-session-ui';
import type { AuthState } from '../auth/auth-service.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
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
 * Sets the open campaign and derives the caller's shell state from its SpiceDB flags (TASK-0644).
 * The gateway returns the flags on each campaign. The DM-only plugins follow `permissions.manage`.
 * The header shows the campaign role as text.
 */
export function setCurrentCampaign(host: RunefobleApp, campaign: CampaignItem | null): void {
  host.currentCampaign = campaign;
  host.userRole = campaign?.role || 'Player';
  registerDefaultPlugins(pluginRegistry, Boolean(campaign?.permissions.manage));
}
