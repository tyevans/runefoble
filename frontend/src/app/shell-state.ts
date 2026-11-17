/**
 * App Shell State Sync (TASK-0640b).
 *
 * Applies the stored theme to the document and mirrors the signed-in user's role onto
 * the host. Plugin slots register again when the role changes.
 */

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

/** Copies the auth state to the host and registers plugins for the user's role. */
export function syncAuthState(host: RunefobleApp, s: AuthState): void {
  host.currentUserId = s.user?.user_id || '';
  host.isDM = Boolean(s.user?.roles.some((r) => ['dm', 'admin', 'owner'].includes(r)));
  host.userRole = host.isDM ? 'Dungeon Master' : 'Player';
  registerDefaultPlugins(pluginRegistry, host.isDM);
}
