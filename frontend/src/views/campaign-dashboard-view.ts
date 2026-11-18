/**
 * Campaign Dashboard View (TASK-0643). Renders the campaign list and loads it from the gateway.
 */

import { html } from 'lit';
import { router } from '../router/index.ts';
import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { failLoad } from '../app/load-error.ts';
import { createCampaignFromEvent } from '../app/campaign-actions.ts';

export async function loadDashboardData(host: RunefobleApp): Promise<void> {
  const res = await appDataService.fetchCampaigns();
  if (!res.ok) return failLoad(host, res);
  host.campaigns = res.data;
}

export function renderDashboard(app: RunefobleApp) {
  return html`<runefoble-campaign-dashboard .campaigns=${app.campaigns} user-id=${app.currentUserId} @select-campaign=${(e: CustomEvent) => router.navigate('#/campaigns/' + e.detail.campaignId)} @create-campaign=${(e: CustomEvent) => createCampaignFromEvent(app, e)}></runefoble-campaign-dashboard>`;
}
