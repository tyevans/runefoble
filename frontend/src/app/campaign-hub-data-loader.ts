/**
 * App Shell Campaign Hub Data Loader (TASK-0646).
 *
 * Loads the atlas, codex, and analytics datasets for the Codex & Lore and Chronicle & Stats
 * tabs through the gateway. A failed read sets loadError, so the tab shows an error state.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { fetchCampaignAnalyticsView, fetchCampaignAtlasView, fetchCampaignLoreEntries } from '../services/campaign-hub-client.ts';
import { failLoad } from './load-error.ts';

const gateway = appDataService.request.bind(appDataService);

export async function loadCodexData(host: RunefobleApp, campaignId: string): Promise<void> {
  const [atlas, lore] = await Promise.all([fetchCampaignAtlasView(gateway, campaignId), fetchCampaignLoreEntries(gateway, campaignId)]);
  if (!atlas.ok || !lore.ok) return failLoad(host, atlas, lore);
  host.campaignAtlas = atlas.data;
  host.campaignLoreEntries = lore.data;
}

export async function loadAnalyticsData(host: RunefobleApp, campaignId: string): Promise<void> {
  const res = await fetchCampaignAnalyticsView(gateway, campaignId);
  if (!res.ok) return failLoad(host, res);
  host.campaignAnalytics = res.data;
}
