/**
 * App Shell Data Loader (TASK-0643).
 *
 * Loads the data that a routed view needs. It runs the header campaign switcher read and
 * the view controller read together. A failed view read sets loadError, so the shell
 * shows an error state with retry.
 */

import type { MatchedRoute } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { VIEW_CONTROLLERS } from '../views/index.ts';

export async function loadRouteData(host: RunefobleApp, route: MatchedRoute): Promise<void> {
  host.loadError = null;
  const controller = VIEW_CONTROLLERS[host.getActiveView()];
  await Promise.all([
    controller.switcher ? loadCampaignSwitcher(host) : undefined,
    controller.load?.(host, route),
  ]);
}

/** Fills the header campaign switcher from the API. A failed read is reported as a toast. */
async function loadCampaignSwitcher(host: RunefobleApp): Promise<void> {
  const res = await appDataService.fetchCampaigns();
  if (res.ok) host.campaigns = res.data;
  else host.showToast(`Campaign list not loaded. ${res.message}`);
}
