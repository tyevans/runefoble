/**
 * App Shell Lore Actions (TASK-0695).
 *
 * Handles the atlas pin-create event. The Codex & Lore component only emits the event. This
 * handler places the pin through the gateway, then reloads the atlas. A refused write sets a
 * visible error on the atlas and leaves the pin list unchanged.
 */

import type { RunefobleApp } from '../runefoble-app.ts';
import { appDataService } from '../services/app-data-service.ts';
import { createAtlasPin, fetchCampaignAtlasView, type AtlasPinPayload } from '../services/campaign-hub-client.ts';
import { failLoad } from './load-error.ts';

export type PinCreateDetail = AtlasPinPayload & { campaignId?: string };

export async function createPinFromEvent(host: RunefobleApp, e: CustomEvent<PinCreateDetail>): Promise<void> {
  const detail = e.detail;
  const campaignId = detail?.campaignId || host.campaignId;
  host.campaignPinError = null;
  const created = await createAtlasPin(appDataService.request.bind(appDataService), campaignId, {
    title: detail.title,
    coordinates: detail.coordinates,
    layer: detail.layer,
  });
  if (!created.ok) {
    host.campaignPinError = `Pin not placed. ${created.message}`;
    return;
  }
  const atlas = await fetchCampaignAtlasView(appDataService.request.bind(appDataService), campaignId);
  if (!atlas.ok) return failLoad(host, atlas);
  host.campaignAtlas = atlas.data;
}
